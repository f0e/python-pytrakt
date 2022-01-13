from time import sleep, time

from trakt.api import HttpClient
from trakt.auth import get_client_info
from trakt.config import AuthConfig


class DeviceAuth:
    def __init__(self, client: HttpClient, config: AuthConfig, client_id=None, client_secret=None, store=False):
        """
        :param client_id: Your Trakt OAuth Application's Client ID
        :param client_secret: Your Trakt OAuth Application's Client Secret
        :param store: Boolean flag used to determine if your trakt api auth data
            should be stored locally on the system. Default is :const:`False` for
            the security conscious
        """
        self.client = client
        self.config = config
        self.client_id = client_id
        self.client_secret = client_secret
        self.store = store

    def authenticate(self):
        """Process for authenticating using device authentication.

        The function will attempt getting the device_id, and provide
        the user with a url and code. After getting the device
        id, a timer is started to poll periodic for a successful authentication.
        This is a blocking action, meaning you
        will not be able to run any other code, while waiting for an access token.

        If you want more control over the authentication flow, use the functions
        get_device_code and get_device_token.
        Where poll_for_device_token will check if the "offline"
        authentication was successful.

        :return: A dict with the authentication result.
        Or False of authentication failed.
        """
        error_messages = {
            404: 'Invalid device_code',
            409: 'You already approved this code',
            410: 'The tokens have expired, restart the process',
            418: 'You explicitly denied this code',
        }

        success_message = (
            "You've been successfully authenticated. "
            "With access_token {access_token} and refresh_token {refresh_token}"
        )

        self.update_tokens()
        response = self.get_device_code()
        device_code = response['device_code']
        interval = response['interval']

        # No need to check for expiration, the API will notify us.
        while True:
            response = self.get_device_token(device_code, self.store)

            if response.status_code == 200:
                print(success_message.format_map(response.json()))
                break

            elif response.status_code == 429:  # slow down
                interval *= 2

            elif response.status_code != 400:  # not pending
                print(error_messages.get(response.status_code, response.reason))
                break

            sleep(interval)

        return response

    def get_device_code(self):
        """Generate a device code, used for device oauth authentication.

        Trakt docs: https://trakt.docs.apiary.io/#reference/
        authentication-devices/device-code
        :return: Your OAuth device code.
        """

        data = {"client_id": self.config.CLIENT_ID}
        response = self.client.post('/oauth/device/code', data=data)

        print('Your user code is: {user_code}, please navigate to {verification_url} to authenticate'.format(
            user_code=response.get('user_code'),
            verification_url=response.get('verification_url')
        ))

        response['requested'] = time()

        return response

    def get_device_token(self, device_code, store=False):
        """
        Trakt docs: https://trakt.docs.apiary.io/#reference/
        authentication-devices/get-token
        Response:
        {
          "access_token": "",
          "token_type": "bearer",
          "expires_in": 7776000,
          "refresh_token": "",
          "scope": "public",
          "created_at": 1519329051
        }
        :return: Information regarding the authentication polling.
        :return type: dict
        """

        data = {
            "code": device_code,
            "client_id": self.config.CLIENT_ID,
            "client_secret": self.config.CLIENT_SECRET
        }
        response = self.client.post('/oauth/device/token', data=data)

        # We only get json on success.
        if response.status_code == 200:
            data = response.json()
            self.config.update(
                OAUTH_TOKEN=data.get('access_token'),
                OAUTH_REFRESH=data.get('refresh_token'),
                OAUTH_EXPIRES_AT=data.get("created_at") + data.get("expires_in"),
            )

            if store:
                self.config.store()

        return response

    def update_tokens(self):
        """
        Update client_id, client_secret from input or ask them interactively
        """
        if self.client_id is None and self.client_secret is None:
            self.client_id, self.client_secret = get_client_info()
        self.config.CLIENT_ID, self.config.CLIENT_SECRET = self.client_id, self.client_secret
