package com.cropcred.passport

import android.net.Uri
import android.util.Base64
import androidx.lifecycle.lifecycleScope
import com.getcapacitor.JSObject
import com.getcapacitor.Plugin
import com.getcapacitor.PluginCall
import com.getcapacitor.PluginMethod
import com.getcapacitor.annotation.CapacitorPlugin
import com.solana.mobilewalletadapter.clientlib.ActivityResultSender
import com.solana.mobilewalletadapter.clientlib.ConnectionIdentity
import com.solana.mobilewalletadapter.clientlib.MobileWalletAdapter
import com.solana.mobilewalletadapter.clientlib.Solana
import com.solana.mobilewalletadapter.clientlib.TransactionResult
import kotlinx.coroutines.launch

@CapacitorPlugin(name = "NativeWallet")
class NativeWalletPlugin : Plugin() {
    private lateinit var adapter: MobileWalletAdapter
    private lateinit var sender: ActivityResultSender

    override fun load() {
        super.load()
        val activity = activity
        sender = ActivityResultSender(activity)
        adapter = MobileWalletAdapter(
            ConnectionIdentity(
                Uri.parse("https://cropcred.onrender.com"),
                Uri.parse("https://cropcred.onrender.com/icon.svg"),
                "CropCred"
            )
        )
        adapter.blockchain = Solana.Devnet
    }

    @PluginMethod
    fun connect(call: PluginCall) {
        activity.lifecycleScope.launch {
            when (val result = adapter.connect(sender)) {
                is TransactionResult.Success -> {
                    val account = result.authResult.accounts.firstOrNull()
                    if (account == null) call.reject("Wallet returned no account")
                    else call.resolve(JSObject().put("publicKey", base58(account.publicKey)))
                }
                is TransactionResult.NoWalletFound -> call.reject(result.message, "WALLET_NOT_FOUND")
                is TransactionResult.Failure -> call.reject(result.message, "WALLET_CONNECTION_FAILED", result.e)
            }
        }
    }

    @PluginMethod
    fun disconnect(call: PluginCall) {
        activity.lifecycleScope.launch {
            when (val result = adapter.disconnect(sender)) {
                is TransactionResult.Success -> call.resolve()
                is TransactionResult.NoWalletFound -> call.resolve()
                is TransactionResult.Failure -> call.reject(result.message, "WALLET_DISCONNECT_FAILED", result.e)
            }
        }
    }

    @PluginMethod
    fun signAndSend(call: PluginCall) {
        val encoded = call.getString("transaction")
        if (encoded.isNullOrBlank()) {
            call.reject("A serialized transaction is required")
            return
        }
        activity.lifecycleScope.launch {
            when (val result = adapter.transact(sender) {
                val payload = Base64.decode(encoded, Base64.NO_WRAP)
                this.signAndSendTransactions(arrayOf(payload)).signatures.firstOrNull()
                    ?: throw IllegalStateException("Wallet returned no transaction signature")
            }) {
                is TransactionResult.Success -> call.resolve(JSObject().put("signature", base58(result.payload)))
                is TransactionResult.NoWalletFound -> call.reject(result.message, "WALLET_NOT_FOUND")
                is TransactionResult.Failure -> call.reject(result.message, "WALLET_TRANSACTION_FAILED", result.e)
            }
        }
    }

    private fun base58(bytes: ByteArray): String {
        val alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        var value = java.math.BigInteger(1, bytes)
        val result = StringBuilder()
        while (value > java.math.BigInteger.ZERO) {
            val remainder = value.mod(java.math.BigInteger.valueOf(58L)).toInt()
            result.append(alphabet[remainder])
            value = value.divide(java.math.BigInteger.valueOf(58L))
        }
        for (byte in bytes) if (byte.toInt() == 0) result.append('1') else break
        return result.reverse().toString()
    }
}
