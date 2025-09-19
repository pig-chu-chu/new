package com.example.feelwithus.data.device

import kotlinx.coroutines.*
import java.net.Socket
import java.io.PrintWriter
import java.io.BufferedReader
import java.io.InputStreamReader

class VrNetworkManager(
    private val ip: String,
    private val port: Int,
    private val onConnected: () -> Unit,
    private val onDisconnected: () -> Unit,
    private val onError: (String) -> Unit
) {
    private var socket: Socket? = null
    private var writer: PrintWriter? = null
    private var reader: BufferedReader? = null
    private val coroutineScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun connect() {
        coroutineScope.launch {
            try {
                socket = Socket(ip, port)
                writer = PrintWriter(socket!!.getOutputStream(), true)
                reader = BufferedReader(InputStreamReader(socket!!.getInputStream()))
                withContext(Dispatchers.Main) { onConnected() }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { onError("連線VR失敗: ${e.message}") }
            }
        }
    }

    fun disconnect() {
        coroutineScope.launch {
            try {
                writer?.close()
                reader?.close()
                socket?.close()
                withContext(Dispatchers.Main) { onDisconnected() }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { onError("斷開VR連線錯誤: ${e.message}") }
            }
        }
    }

    fun sendCommand(command: String) {
        coroutineScope.launch {
            try {
                writer?.println(command)
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { onError("發送VR命令失敗: ${e.message}") }
            }
        }
    }
}
