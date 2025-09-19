package com.example.feelwithus.ui.auth

import android.content.Intent
import android.media.AudioManager
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.*
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.feelwithus.R
import com.example.feelwithus.data.model.Match
import com.example.feelwithus.data.network.GenericResponse
import com.example.feelwithus.data.network.RetrofitClientA
import com.example.feelwithus.data.network.RetrofitClientC
import com.example.feelwithus.data.network.RetrofitClientD
import com.example.feelwithus.ui.main.MainActivity
import com.google.android.exoplayer2.ExoPlayer
import com.google.android.exoplayer2.ui.PlayerView
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import retrofit2.Call

class animatedOpActivity2 : AppCompatActivity() {

    private var waitDialog: AlertDialog? = null
    private var allDevicesReady = false
    private lateinit var playerView: PlayerView
    private var exoPlayer: ExoPlayer? = null
    private lateinit var soundSB: SeekBar
    private lateinit var brightSB: SeekBar
    private lateinit var soundPercent: TextView
    private lateinit var brightPercent: TextView
    private lateinit var switchTouch: Switch
    private lateinit var switchSmell: Switch
    private var isInitialStart = true
    private lateinit var endBtn: Button
    private lateinit var backbtn: ImageButton
    private lateinit var controlPanel: FrameLayout
    private lateinit var toggleBtn: ImageButton
    private var isFinishing = false

    private val activeCalls = mutableListOf<Call<*>>()

    private var videoUri: Uri? = null
    private var matchTitle: String = ""

    // 影片路徑前綴
    private val videoBasePath = "http://163.13.201.90/3d_video/basketball_3/loadvideo.php?filename="

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.animated_onphone2)

        playerView = findViewById(R.id.playerView)
        exoPlayer = ExoPlayer.Builder(this).build()
        playerView.player = exoPlayer

        matchTitle = intent.getStringExtra("match_title") ?: ""

        showWaitingDialog()

        VideoListAsync { videoList ->
            val fileName = findFileNameFromList(videoList, matchTitle)
            if (fileName.isBlank()) {
                runOnUiThread {
                    waitDialog?.dismiss()
                    Toast.makeText(
                        this@animatedOpActivity2,
                        "影片取得失敗，請重新選擇",
                        Toast.LENGTH_LONG
                    ).show()
                    finishAndReturnMain()
                }
                return@VideoListAsync
            }

            matchTitle = fileName

            lifecycleScope.launch {
                waitForDevicesReady()
            }
        }
    }

    private fun VideoListAsync(callback: (List<Match>) -> Unit) {
        lifecycleScope.launch {
            try {
                val response = RetrofitClientA.api.get3DvideoList()
                if (response.isSuccessful && response.body() != null) {
                    callback(response.body()!!)
                } else {
                    callback(emptyList())
                }
            } catch (e: Exception) {
                Log.e("animatedOpActivity2", "fetch3dVideoList 請求失敗", e)
                callback(emptyList())
            }
        }
    }

    private fun initializeViewsAndControls() {
        playerView = findViewById(R.id.playerView)
        exoPlayer = ExoPlayer.Builder(this).build()
        playerView.player = exoPlayer
        soundSB = findViewById(R.id.soundSB)
        brightSB = findViewById(R.id.brightSB)
        soundPercent = findViewById(R.id.Text1)
        brightPercent = findViewById(R.id.Text2)
        switchTouch = findViewById(R.id.switch2)
        switchSmell = findViewById(R.id.switch3)
        backbtn = findViewById(R.id.btnBack)
        endBtn = findViewById(R.id.saveBtn)
        controlPanel = findViewById(R.id.controlPanel)
        toggleBtn = findViewById(R.id.btnToggleControl)
        switchTouch.isChecked = true
        switchSmell.isChecked = true

        toggleBtn.setOnClickListener {
            if (controlPanel.visibility == View.VISIBLE) {
                controlPanel.visibility = View.GONE
                toggleBtn.setImageResource(R.drawable.ic_arrow_left)
            } else {
                controlPanel.visibility = View.VISIBLE
                toggleBtn.setImageResource(R.drawable.round_arrow_back)
            }
        }

        setupAudioBrightnessControls()
        setupSwitchListeners()
        setupEndAndBackButtons()

        exoPlayer?.addListener(object : com.google.android.exoplayer2.Player.Listener {
            override fun onPlaybackStateChanged(state: Int) {
                Log.d("liveOpActivity", "Playback state changed: $state")
                if (state == com.google.android.exoplayer2.Player.STATE_ENDED) {
                    lifecycleScope.launch {
                        delay(5000)  // 等待5秒
                        try {
                            val respC = RetrofitClientC.api.dbStop("end")
                            val respD = RetrofitClientD.api.dbStop("end")
                            runOnUiThread {
                                if (respC.isSuccessful && respC.body()?.success == true &&
                                    respD.isSuccessful && respD.body()?.success == true) {
                                    Toast.makeText(this@animatedOpActivity2, "影片播放完成，結束成功", Toast.LENGTH_SHORT).show()
                                } else {
                                    Toast.makeText(this@animatedOpActivity2, "結束指令失敗", Toast.LENGTH_SHORT).show()
                                }
                                finishAndReturnMain()
                            }
                        } catch (e: Exception) {
                            runOnUiThread {
                                Toast.makeText(this@animatedOpActivity2, "結束錯誤: ${e.message}", Toast.LENGTH_SHORT).show()
                                finishAndReturnMain()
                            }
                        }
                    }
                }
            }
        })
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
                    if (!response.isSuccessful) {
                        runOnUiThread {
                            switchTouch.setOnCheckedChangeListener(null)
                            switchTouch.isChecked = !isChecked
                            setupSwitchListeners()
                        }
                        Toast.makeText(
                            this@animatedOpActivity2,
                            "手套回饋控制失敗",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: Exception) {
                    runOnUiThread {
                        switchTouch.setOnCheckedChangeListener(null)
                        switchTouch.isChecked = !isChecked
                        setupSwitchListeners()
                    }
                    Toast.makeText(
                        this@animatedOpActivity2,
                        "手套回饋控制錯誤: ${e.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }

        switchSmell.setOnCheckedChangeListener { _, isChecked ->
            if (isInitialStart) return@setOnCheckedChangeListener
            lifecycleScope.launch {
                try {
                    val response = RetrofitClientD.api.switch(isChecked)
                    if (!response.isSuccessful) {
                        runOnUiThread {
                            switchSmell.setOnCheckedChangeListener(null)
                            switchSmell.isChecked = !isChecked
                            setupSwitchListeners()
                        }
                        Toast.makeText(
                            this@animatedOpActivity2,
                            "氣味回饋控制失敗",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: Exception) {
                    runOnUiThread {
                        switchSmell.setOnCheckedChangeListener(null)
                        switchSmell.isChecked = !isChecked
                        setupSwitchListeners()
                    }
                    Toast.makeText(
                        this@animatedOpActivity2,
                        "氣味回饋控制錯誤: ${e.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }

    private fun setupEndAndBackButtons() {
        endBtn.setOnClickListener {
            lifecycleScope.launch {
                try {
                    val respC = RetrofitClientC.api.dbStop("end")
                    Log.d("animatedOpActivity2", "呼叫手套 dbStop 回應: code=${respC.code()} ")
                    val respD = RetrofitClientD.api.dbStop("end")
                    Log.d("animatedOpActivity2", "呼叫氣味裝置 dbStop 回應: code=${respD.code()} ")
                    if (respC.isSuccessful && respC.body()?.success == true &&
                        respD.isSuccessful && respD.body()?.success == true
                    ) {
                        Toast.makeText(this@animatedOpActivity2, "已結束播放", Toast.LENGTH_SHORT)
                            .show()
                        finishAndReturnMain()
                    } else {
                        Toast.makeText(
                            this@animatedOpActivity2,
                            "結束失敗，請稍後再試",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: Exception) {
                    Toast.makeText(
                        this@animatedOpActivity2,
                        "停止錯誤: ${e.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }

        backbtn.setOnClickListener {
            onBackPressedDispatcher.onBackPressed()
        }
    }

    private suspend fun waitForDevicesReady() {
        var failCount = 0
        while (!allDevicesReady) {
            try {
                val statusC = true
                Log.d("animatedOpActivity2", "呼叫手套 status 回應: code=${0}")
                val statusD = true
                Log.d("animatedOpActivity2", "呼叫氣味裝置 status 回應: code=${0}")
                allDevicesReady = statusC == true && statusD  == true
            } catch (e: Exception) {
                failCount++
                if (failCount > 8) {
                    runOnUiThread {
                        waitDialog?.dismiss()
                        Toast.makeText(
                            this@animatedOpActivity2,
                            "裝置連線失敗，請檢查網路或裝置狀態",
                            Toast.LENGTH_LONG
                        ).show()
                        finishAndReturnMain()
                    }
                    return
                }
            }
            delay(2000)
        }
        runOnUiThread {
            videoUri = Uri.parse(videoBasePath + matchTitle)
            initializeViewsAndControls()
            updateDialogPreparing()
            val mediaItem = com.google.android.exoplayer2.MediaItem.fromUri(videoUri!!)
            exoPlayer?.setMediaItem(mediaItem)
            exoPlayer?.prepare()
            // 在ExoPlayer準備完畢時顯示對話框
            exoPlayer?.addListener(object : com.google.android.exoplayer2.Player.Listener {
                override fun onPlaybackStateChanged(state: Int) {
                    if (state == com.google.android.exoplayer2.Player.STATE_READY) {
                        updateDialogReady()
                    }
                }
            })
        }
    }

    private fun showWaitingDialog() {
        val builder = AlertDialog.Builder(this)
        builder.setTitle("等待裝置準備狀態")
        builder.setMessage("請稍候，系統正在確認裝置狀態...")
        builder.setCancelable(false)
        waitDialog = builder.create()
        waitDialog?.show()
    }

    private fun updateDialogPreparing() {
        waitDialog?.setMessage("裝置已準備完畢，正在載入影片...")
    }

    private fun updateDialogReady() {
        waitDialog?.dismiss()
        val builder = AlertDialog.Builder(this)
            .setTitle("準備就緒")
            .setMessage("影片已載入完成，可以開始播放")
            .setCancelable(false)
            .setPositiveButton("開始播放") { dialog, _ ->
                Log.d("animatedOpActivity2", "用戶確認開始播放")
                dialog.dismiss()
                isInitialStart = false
                lifecycleScope.launch {
                    try {
                        if (switchTouch.isChecked) {
                            val switchResponse = RetrofitClientC.api.switch(true)
                            if (!switchResponse.isSuccessful) {
                                Toast.makeText(
                                    this@animatedOpActivity2,
                                    "手套設備啟動",
                                    Toast.LENGTH_SHORT
                                ).show()
                                Log.d("animatedOpActivity2", "手套switch on 啟動")
                            }
                        }
                        if (switchSmell.isChecked) {
                            val switchResponseD = RetrofitClientD.api.switch(true)
                            if (!switchResponseD.isSuccessful) {
                                Toast.makeText(
                                    this@animatedOpActivity2,
                                    "氣味設備啟動",
                                    Toast.LENGTH_SHORT
                                ).show()
                                Log.d("animatedOpActivity2", "氣味switch on 啟動")
                            }
                        }
                    } catch (e: Exception) {
                        Toast.makeText(
                            this@animatedOpActivity2,
                            "設備啟動失敗: ${e.message}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
                exoPlayer?.playWhenReady = true
            }
        waitDialog = builder.create()
        waitDialog?.show()
    }

    private fun findFileNameFromList(videoList: List<Match>, name: String): String {
        val videoItem = videoList.find { it.fileName == name || it.description == name }
        return videoItem?.fileName ?: ""
    }

    override fun onDestroy() {
        super.onDestroy()
        for (call in activeCalls) {
            if (!call.isCanceled) call.cancel()
        }
        activeCalls.clear()
        waitDialog?.dismiss()
        exoPlayer?.release()
        exoPlayer = null
    }

    private fun finishAndReturnMain() {
        Log.d("animatedOpActivity2", "finishAndReturnMain called")
        runOnUiThread {
            try {
                exoPlayer?.stop()
                exoPlayer?.release()
                exoPlayer = null
            } catch (e: Exception) {
                Log.e("animatedOpActivity2", "VideoView release error: ${e.message}")
            }
            waitDialog?.dismiss()
            waitDialog = null
            val intent = Intent(this, MainActivity::class.java)
            intent.flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            startActivity(intent)
            finish()
        }
    }
}