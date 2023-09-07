from ...core import Storjapi, Storjnodedata, Storjpayoutdata, ApiRequestFailedException

class Storjhost:
    def __init__(self, plugin, name, host):
        self.__plugin = plugin
        self.__api = Storjapi(host, self.__plugin)
        self.__name = name
        self.__id = None

    def __eq__(self, other):
        return other.name == self.__name

    def __hash__(self):
        return hash(self.name)

    async def check(self, session):
        try:
            data = Storjnodedata(await self.__api.get(session, 'sno/'))
        except ApiRequestFailedException:
            self.__plugin.alert(f'{self.__name}_online', f"'{self.__name}': node healthcheck failed.")
            return
        self.__plugin.reset_alert(f'{self.__name}_online', f"'{self.__name}': node healthcheck is successful again.")
        
        self.__id = data.id
        
        if not data.uptodate:
            self.__plugin.alert(f'{self.__name}_version', f"'{self.__name}': node version is outdated.")
        else:
            self.__plugin.reset_alert(f'{self.__name}_version', f"'{self.__name}': node version is up to date.")

        if not data.quic:
            self.__plugin.alert(f'{self.__name}_quic', f"'{self.__name}': QUIC is disabled.")
        else:
            self.__plugin.reset_alert(f'{self.__name}_quic', f"'{self.__name}': QUIC is enabled again.")

        if data.satellites == 0:
            self.__plugin.alert(f'{self.__name}_sat', f"'{self.__name}' is offline.")
        else:
            self.__plugin.reset_alert(f'{self.__name}_sat', f"'{self.__name}' is online again, {data.satellites} satellites.")

        if data.disqualified > 0:
            self.__plugin.alert(f'{self.__name}_disq', f"'{self.__name}' is disqualified for {data.disqualified} satellites.")
        else:
            self.__plugin.reset_alert(f'{self.__name}_disq', f"'{self.__name}' is no longer disqualified for any satellite.")

        if data.suspended > 0:
            self.__plugin.__plugin.alert(f'{self.__name}_susp', f"'{self.__name}' is suspended for {data.disqualified} satellites.")
        else:
            self.__plugin.reset_alert(f'{self.__name}_susp', f"'{self.__name}' is no longer suspended for any satellite.")

        if data.overused_space > 0:
            self.__plugin.alert(f'{self.__name}_overu', f"'{self.__name}' overuses {data.overused_space} bytes storage.")
        else:
            self.__plugin.reset_alert(f'{self.__name}_overu', f"'{self.__name}' does no longer overuse storage.")

    async def get_node_info(self, session):
        info = Storjnodedata(await self.__api.get(session, 'sno/'))
        self.__id = info.id
        return info
    
    async def get_payout_info(self, session):
        if self.__id is None:
            self.__id = Storjnodedata(await self.__api.get(session, 'sno/')).id
        return Storjpayoutdata(await self.__api.get(session, 'sno/estimated-payout'))

    @property
    def name(self):
        return self.__name
    
    @property
    def id(self):
        return self.__id