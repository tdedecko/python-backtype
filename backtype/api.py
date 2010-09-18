from exceptions import Exception
from urllib import urlencode
import urllib2

try:
    import json
except ImportError:
    import simplejson as json


class BacktypeError(Exception):
    """Exception raised by Backtype API."""
    pass


class BacktypeRequestError(BacktypeError):
    """Exception to handle Backtype API response errors."""
    pass


class Backtype(object):

    def __init__(self, key, user_agent=None):
        self._key = key
	self._user_agent = user_agent

        self._action_name = ''
        self._config_params = {}

        self._cached_action_name = None
        self._cached_params = None

        self.response = ''
        self.items_per_page = None # Between 10-100
        self._page = None

    def __getattribute__(self, k):
        try:
            return object.__getattribute__(self, k)
        except AttributeError:
            self._action_name = '.'.join((self._action_name, k)).lstrip('.')
            return self

    def __call__(self, **params):
        # Check if action is valid.
	action_name = self._action_name
	if not action_name in ACTIONS.keys():
            self._cleanup()
            raise BacktypeError('%s is an unsupported action.' % action_name)

        # Get action and build params
        action = ACTIONS[action_name]
	self._build_config_params()
        request_params = params.copy()
        request_params.update(self._config_params)
        self._cleanup() # Cleanup in case of unexpected failure.

        # Build request.
        request_url = action.build_request_url(request_params)
        request = urllib2.Request(request_url)

        if not self._user_agent is None:
	    request.add_header('User-Agent', self._user_agent)

        try:
            handle = urllib2.urlopen(request)
            response = handle.read()
	    response = json.loads(response)
        except urllib2.HTTPError:
            raise BacktypeError('Unable to connect to Backtype using action: %s' % action_name)
        except urllib2.URLError:
            raise BacktypeError('Unable to handle URL: %s' % request_url)
        except ValueError:
            raise BacktypeError('Response was not json: %s' % response)

        # Clean up and cache response.
	self._cache_action(action_name, params, response)
        return response

    def _cache_action(self, action_name, params, response):
        """Cache action and clear current action."""
        self._cached_action_name = action_name
        self._cached_params = params.copy()
        self.response = response

    def _build_config_params(self):
        self._config_params['key'] = self._key

        if not self._page is None:
            self._config_params['page'] = self._page

        if not self.items_per_page is None:
            self._config_params['itemsperpage'] = self.items_per_page

    def _cleanup(self):
        self._action_name = ''
        self._config_params = {}
        

class Action(object):

    def __init__(self, url_format, req_params, std_params=True):
        self.url_format = url_format
        self.req_params = req_params
	self.std_params = std_params

        self.BASE_URL = 'http://api.backtype.com'

    def build_request_url(self, params):
        self._check_req_params(params)
        action = self._format_url_action(params)

        request_url = '%s%s?%s' % (self.BASE_URL, action, urlencode(params))
        return request_url

    def _check_req_params(self, params):
        for param in self.req_params:
            if not param in params.keys():
                raise BacktypeError("'%s' parameter is required for action" % param)

    def _format_url_action(self, params):
        # Handle non-standard params
        if not self.std_params:
            param_tuple = ()
            for param in self.req_params:
                param_tuple += (params[param],)
                del params[param]
            return self.url_format % param_tuple

        return self.url_format


ACTIONS = {}
ACTIONS['comments.search'] = Action('/comments/search.json', ['q'])
ACTIONS['comments.connect'] = Action('/comments/connect.json', ['url'])
ACTIONS['comments.connect.stats'] = Action('/comments/connect/stats.json', ['url'])
ACTIONS['url.comments'] = Action('/url/%s/comments.json', ['url'], std_params=False)
ACTIONS['post.comments'] = Action('/post/comments.json', ['url'])
ACTIONS['post.stats'] = Action('/post/stats.json', ['url'])
ACTIONS['tweetcount'] = Action('/tweetcount.json', ['q'])
