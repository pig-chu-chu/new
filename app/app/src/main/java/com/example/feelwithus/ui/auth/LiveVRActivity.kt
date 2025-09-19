package com.example.feelwithus.ui.auth

import android.content.Intent
import android.content.pm.ActivityInfo
import android.media.AudioManager
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.View
import android.view.Window
import android.view.WindowManager
import android.widget.*
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.Player
import com.google.android.exoplayer2.MediaItem
import com.google.android.exoplayer2.ui.PlayerView
import com.example.feelwithus.R
import com.example.feelwithus.data.model.Match
import com.example.feelwithus.data.network.RetrofitClientA
import com.example.feelwithus.data.network.RetrofitClientC
import com.example.feelwithus.data.network.RetrofitClientD
import com.example.feelwithus.data.network.RetrofitClientE
import com.example.feelwithus.ui.main.MainActivity

import com.google.ar.sceneform.Node
import com.google.ar.sceneform.SceneView
import com.google.ar.sceneform.math.Vector3
import com.google.ar.sceneform.rendering.ExternalTexture
import com.google.ar.sceneform.ux.TransformableNode
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import retrofit2.Call

class LiveVRActivity : AppCompatActivity() {
    private lateinit var waitDialog: AlertDialog
    private var allDevicesReady = false
    private lateinit var soundSB: SeekBar
    private lateinit var brightSB: SeekBar
    private lateinit var soundPercent: TextView
    private lateinit var brightPercent: TextView
    private lateinit var switchTouch: Switch
    private lateinit var switchSmell: Switch
    private lateinit var backbtn: ImageButton
    private lateinit var endBtn: Button
    private lateinit var controlPanel: View

    private var videoName: String = ""
    private var isInitialStart = true
    private var isFinishing = false

    private val activeCalls = mutableListOf<Call<*>>()

    // private val videoBasePath = "http://163.13.201.90/video/uploads/loadvideo.php?filename="
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_live_vr)

        videoName = "volleyball_1.mp4"
        initializeViewsAndControls()

        showWaitingDialog()
        lifecycleScope.launch {
            waitForDevicesReady()
        }
    }

    private fun initializeViewsAndControls() {
        soundSB = findViewById(R.id.soundSB)
        brightSB = findViewById(R.id.brightSB)
        soundPercent = findViewById(R.id.Text1)
        brightPercent = findViewById(R.id.Text2)
        switchTouch = findViewById(R.id.switch2)
        switchSmell = findViewById(R.id.switch3)
        backbtn = findViewById(R.id.btnBack)
        endBtn = findViewById(R.id.saveBtn)
        controlPanel = findViewById(R.id.controlPanel)

        switchTouch.isChecked = true
        switchSmell.isChecked = true

        setupAudioBrightnessControls()
        setupSwitchListeners()
        setupEndAndBackButtons()
    }

    private fun setupAudioBrightnessControls() {
        val audioManager = getSystemService(AUDIO_SERVICE) as AudioManager
        soundSB.max = audioManager.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        soundSB.progress = audioManager.getStreamVolume(AudioManager.STREAM_MUSIC)
        val soundMax = soundSB.max
        soundPercent.text = "${(soundSB.progress * 100 / soundMax)}%"
        soundSB.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                audioManager.setStreamVolume(AudioManager.STREAM_MUSIC, progress, 0)
                soundPercent.text = "${(progress * 100 / soundMax)}%"
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        brightSB.max = 100
        val currentBrightness = window.attributes.screenBrightness
        val brightnessInit = if (currentBrightness >= 0f) (currentBrightness * 100).toInt() else 100
        brightSB.progress = brightnessInit
        brightPercent.text = "$brightnessInit%"
        brightSB.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, progress: Int, fromUser: Boolean) {
                val brightness = (progress / 100f).coerceAtLeast(0.01f)
                val lp = window.attributes
                lp.screenBrightness = brightness
                window.attributes = lp
                brightPercent.text = "$progress%"
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })
    }

    private fun setupSwitchListeners() {
        switchTouch.setOnCheckedChangeListener { _, isChecked ->
            if (isInitialStart) return@setOnCheckedChangeListener
            lifecycleScope.launch {
                try {
                    val response = RetrofitClientC.api.switch(isChecked)
                    Log.d("LiveVRActivity", "呼叫手套 回應: code=${response}")
                    if (!response.isSuccessful) {
                        runOnUiThread {
                            switchTouch.setOnCheckedChangeListener(null)
                            switchTouch.isChecked = !isChecked
                            setupSwitchListeners()
                        }
                        Toast.makeText(this@LiveVRActivity, "手套回饋控制失敗", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    runOnUiThread {
                        switchTouch.setOnCheckedChangeListener(null)
                        switchTouch.isChecked = !isChecked
                        setupSwitchListeners()
                    }
                    Toast.makeText(this@LiveVRActivity, "手套回饋控制錯誤: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }

        switchSmell.setOnCheckedChangeListener { _, isChecked ->
            if (isInitialStart) return@setOnCheckedChangeListener
            lifecycleScope.launch {
                try {
                    val response = RetrofitClientD.api.switch(isChecked)
                    Log.d("LiveVRActivity", "呼叫氣味 回應: code=${response}")
                    if (!response.isSuccessful) {
                        runOnUiThread {
                            switchSmell.setOnCheckedChangeListener(null)
                            switchSmell.isChecked = !isChecked
                            setupSwitchListeners()
                        }
                        Toast.makeText(this@LiveVRActivity, "氣味回饋控制失敗", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    runOnUiThread {
                        switchSmell.setOnCheckedChangeListener(null)
                        switchSmell.isChecked = !isChecked
                        setupSwitchListeners()
                    }
                    Toast.makeText(this@LiveVRActivity, "氣味回饋控制錯誤: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun setupEndAndBackButtons() {
        endBtn.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val respC = RetrofitClientC.api.dbStop("end")
                    Log.d("LiveVRActivity", "呼叫手套 回應: code=${respC}")
                    val respD = RetrofitClientD.api.dbStop("end")
                    Log.d("LiveVRActivity", "呼叫氣味 回應: code=${respD}")
                    val respOff = RetrofitClientE.api.pauseVideo()
                    Log.d("AnimatedVRActivity", "呼叫E 回應: code=${respOff}")
                    if (!respOff.isSuccessful) {
                        Toast.makeText(this@LiveVRActivity, "停止影片播放失敗", Toast.LENGTH_SHORT).show()
                    }

                    if (respC.isSuccessful && respC.body()?.success == true &&
                        respD.isSuccessful && respD.body()?.success == true) {
                        Toast.makeText(this@LiveVRActivity, "已結束播放", Toast.LENGTH_SHORT).show()
                        finishAndReturnMain()
                    } else {
                        Toast.makeText(this@LiveVRActivity, "結束失敗，請稍後再試", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@LiveVRActivity, "停止錯誤: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        backbtn.setOnClickListener {
            finishAndReturnMain()
        }
    }

    private fun showWaitingDialog() {
        val builder = AlertDialog.Builder(this)
            .setTitle("等待裝置準備狀態")
            .setMessage("請稍候，系統正在確認裝置狀態...")
            .setCancelable(false)
        waitDialog = builder.create()
        waitDialog.show()
    }

    private fun updateDialogReady() {
        runOnUiThread {
            waitDialog.dismiss()
            waitDialog = AlertDialog.Builder(this)
                .setTitle("等待裝置準備狀態")
                .setMessage("裝置已準備完畢，按下開始觀看")
                .setCancelable(false)
                .setPositiveButton("開始觀看") { dialog, _ ->
                    dialog.dismiss()
                    isInitialStart = false
                    lifecycleScope.launch {
                        try {
                            if (switchTouch.isChecked) {
                                val respC = RetrofitClientC.api.switch(true)
                                Log.d("LiveVRActivity", "呼叫手套 回應: code=${respC}")
                                if (!respC.isSuccessful) {
                                    Toast.makeText(this@LiveVRActivity, "手套設備啟動失敗", Toast.LENGTH_SHORT).show()
                                }
                            }
                            if (switchSmell.isChecked) {
                                val respD = RetrofitClientD.api.switch(true)
                                Log.d("LiveVRActivity", "呼叫氣味 回應: code=${respD}")
                                if (!respD.isSuccessful) {
                                    Toast.makeText(this@LiveVRActivity, "氣味設備啟動失敗", Toast.LENGTH_SHORT).show()
                                }
                            }
                            val respVideo = RetrofitClientE.api.switchToVolleyball1()
                            Log.d("AnimatedVRActivity", "呼叫E 回應: code=${respVideo}")
                            if (!respVideo.isSuccessful) {
                                Toast.makeText(this@LiveVRActivity, "切換影片失敗", Toast.LENGTH_SHORT).show()
                            }
                            val respOn = RetrofitClientE.api.playVideo()
                            Log.d("AnimatedVRActivity", "呼叫E 回應: code=${respOn}")
                            if (!respOn.isSuccessful) {
                                Toast.makeText(this@LiveVRActivity, "啟動影片播放失敗", Toast.LENGTH_SHORT).show()
                            }
                        } catch (e: Exception) {
                            Toast.makeText(this@LiveVRActivity, "設備啟動失敗: ${e.message}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
                .create()
            waitDialog.show()
        }
    }

    private suspend fun waitForDevicesReady() {
        var failCount = 0
        while (!allDevicesReady) {
            try {
                val statusC = true // RetrofitClientC.api.status()
                val statusD = true // RetrofitClientD.api.status()
                allDevicesReady = statusC == true && statusD == true
            } catch (e: Exception) {
                failCount++
                if (failCount > 8) {
                    runOnUiThread {
                        waitDialog.dismiss()
                        Toast.makeText(this@LiveVRActivity, "裝置連線失敗，請稍後重試", Toast.LENGTH_LONG).show()
                        finishAndReturnMain()
                    }
                    return
                }
            }
            delay(2000)
        }

        try {
            val switchResponse = RetrofitClientE.api.switchToBasketball1()
            Log.d("AnimatedVRActivity", "呼叫E 回應: code=${switchResponse}")
            if (!switchResponse.isSuccessful) {
                runOnUiThread {
                    Toast.makeText(this@LiveVRActivity, "切換影片失敗，請稍後再試", Toast.LENGTH_LONG).show()
                }
            }
        } catch (e: Exception) {
            runOnUiThread {
                Toast.makeText(this@LiveVRActivity, "切換影片錯誤: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }

        runOnUiThread {
            updateDialogReady()
        }
    }

    private fun finishAndReturnMain() {
        if (!isFinishing) {
            isFinishing = true
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
            finish()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        for (call in activeCalls) {
            if (!call.isCanceled) call.cancel()
        }
        activeCalls.clear()
    }
}
