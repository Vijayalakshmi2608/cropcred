package com.cropcred.passport;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    public MainActivity() {
        registerPlugin(NativeWalletPlugin.class);
    }
}
