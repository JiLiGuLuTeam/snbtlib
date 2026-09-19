# -*- coding: utf-8 -*-
# pylint: disable=undefined-variable,used-before-assignment,too-many-function-args,access-member-before-definition,unsubscriptable-object,no-value-for-parameter,no-name-in-module,no-method-argument,no-self-argument
from mod.common.mod import Mod

@Mod.Binding(name="snbtlib", version="1.0") # type: ignore
class SnbtLib(object):
    """纯库前置模组: 不注册任何 System,只让 snbtlib 包随行为包一起被引擎加载"""

    @Mod.InitServer() # type: ignore
    def init_server(self):
        pass

    @Mod.InitClient() # type: ignore
    def init_client(self):
        pass
