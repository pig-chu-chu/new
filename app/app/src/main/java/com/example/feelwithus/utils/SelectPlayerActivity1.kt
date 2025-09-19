package com.example.feelwithus.utils

import android.content.Intent
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.graphics.RectF
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.*
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import com.example.feelwithus.R
import com.example.feelwithus.ui.main.MainActivity
import com.example.feelwithus.ui.auth.LiveVRActivity
import kotlinx.coroutines.*
import com.example.feelwithus.data.network.JerseyBody
import com.example.feelwithus.data.network.RetrofitClientB
import com.example.feelwithus.data.network.RoiBody
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

class SelectPlayerActivity1 : AppCompatActivity() {

    private lateinit var backbtn: ImageButton
    private lateinit var playerImageView: ImageView
    private lateinit var selectRectView: SelectRectView
    private lateinit var buttonConfirm: Button
    private lateinit var buttonCancel: Button
    private var progressBar: ProgressBar? = null  // 改為可空變數

    private val scope = CoroutineScope(Dispatchers.Main)
    private var isAnalysisRunning = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_select_player)

        // UI元件初始化
        initViews()

        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        startAnalysisAndLoadFrame()

        buttonConfirm.setOnClickListener {
            val selectedRect = selectRectView.getSelectedRect()
            if (selectedRect == null || selectedRect.isEmpty) {
                Toast.makeText(this, "請先框選球員範圍", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val imageRect = convertViewRectToImage(selectedRect)
            if (imageRect == null) {
                Toast.makeText(this, "無法取得圖片範圍", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val roi = listOf(
                imageRect.left.toInt(),
                imageRect.top.toInt(),
                (imageRect.right - imageRect.left).toInt(),
                (imageRect.bottom - imageRect.top).toInt()
            )

            if (isAnalysisRunning) {
                Toast.makeText(this, "分析已啟動，請稍候", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            // 顯示loading
            showLoadingState()

            // 依序呼叫後端並觸發分析
            scope.launch {
                try {
                    val postRoiResponse = RetrofitClientB.api.submitRoi(RoiBody(roi))
                    if (!postRoiResponse.isSuccessful) {
                        Toast.makeText(this@SelectPlayerActivity1, "提交區域失敗", Toast.LENGTH_SHORT).show()
                        resetLoadingState()
                        return@launch
                    }

                    val ocrNumber = postRoiResponse.body()?.ocr ?: "00"
                    Log.d("API", "OCR Number from API: $ocrNumber")

                    showConfirmWithModifyDialog(ocrNumber) { confirmedNumber ->
                        scope.launch {
                            try {
                                while (true) {
                                    val runResponse = RetrofitClientB.api.runAnalysis()
                                    if (runResponse.isSuccessful) {
                                        isAnalysisRunning = true
                                        Log.d("API", "Run analysis started successfully")
                                        resetLoadingState()
                                        startActivity(Intent(this@SelectPlayerActivity1, LiveVRActivity::class.java))
                                        startSharingWithAI(confirmedNumber)
                                        finish()
                                        break
                                    } else if (runResponse.code() == 409) {
                                        delay(3000)
                                    } else {
                                        Toast.makeText(this@SelectPlayerActivity1, "啟動分析失敗", Toast.LENGTH_SHORT).show()
                                        resetLoadingState()
                                        break
                                    }
                                }
                            } catch (e: Exception) {
                                Log.e("API", "啟動分析異常", e)
                                Toast.makeText(this@SelectPlayerActivity1, "發生錯誤，請稍後再試", Toast.LENGTH_SHORT).show()
                                resetLoadingState()
                            }
                        }
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@SelectPlayerActivity1, "網路錯誤: ${e.message}", Toast.LENGTH_SHORT).show()
                    resetLoadingState()
                }
            }
        }

        buttonCancel.setOnClickListener {
            finish()
        }

        backbtn.setOnClickListener {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }

    private fun initViews() {
        try {
            playerImageView = findViewById(R.id.playerImageView)
            selectRectView = findViewById(R.id.selectRectView)
            buttonConfirm = findViewById(R.id.buttonConfirm)
            buttonCancel = findViewById(R.id.buttonCancel)
            backbtn = findViewById(R.id.btnBack)

            // 嘗試初始化 ProgressBar，如果佈局中沒有就設為 null
            progressBar = try {
                findViewById(R.id.progressBar)
            } catch (e: Exception) {
                Log.w("SelectPlayerActivity1", "ProgressBar not found in layout, using null")
                null
            }
        } catch (e: Exception) {
            Log.e("SelectPlayerActivity1", "Error initializing views", e)
            Toast.makeText(this, "初始化介面失敗", Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    private fun showLoadingState() {
        progressBar?.visibility = View.VISIBLE
        buttonConfirm.isEnabled = false
        buttonCancel.isEnabled = false
    }

    private fun resetLoadingState() {
        progressBar?.visibility = View.GONE
        buttonConfirm.isEnabled = true
        buttonCancel.isEnabled = true
    }

    private fun showConfirmWithModifyDialog(recognizedNumber: String, onConfirm: (String) -> Unit) {
        val dialogView = layoutInflater.inflate(R.layout.dialog_confirm_number, null)
        val tvRecognizedNumber = dialogView.findViewById<TextView>(R.id.tvRecognizedNumber)
        val etManualNumber = dialogView.findViewById<EditText>(R.id.etNumber)
        val layoutInputArea = dialogView.findViewById<View>(R.id.inputArea)

        tvRecognizedNumber.text = "辨識背號：$recognizedNumber"
        layoutInputArea.visibility = View.GONE

        val dialogBuilder = AlertDialog.Builder(this)
            .setTitle("確認背號")
            .setView(dialogView)
            .setPositiveButton("確定", null)
            .setNeutralButton("修改", null)
            .setNegativeButton("取消", null)

        val dialog = dialogBuilder.create()
        dialog.show()

        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            val finalNumber =
                if (layoutInputArea.visibility == View.VISIBLE)
                    etManualNumber.text.toString().trim()
                else
                    recognizedNumber
            if (finalNumber.isEmpty()) {
                Toast.makeText(this, "背號不能為空", Toast.LENGTH_SHORT).show()
            } else {
                dialog.dismiss()
                onConfirm(finalNumber)
            }
        }

        dialog.getButton(AlertDialog.BUTTON_NEUTRAL).setOnClickListener {
            layoutInputArea.visibility = View.VISIBLE
            etManualNumber.setText(recognizedNumber)
            etManualNumber.requestFocus()
        }
    }

    private fun startAnalysisAndLoadFrame() {
        scope.launch {
            try {
                val startResponse = RetrofitClientB.api.startAnalysis()
                if (startResponse.isSuccessful) {
                    val frameResponse = RetrofitClientB.api.getFirstFrame()
                    if (frameResponse.isSuccessful) {
                        val responseBody = frameResponse.body()
                        if (responseBody != null) {
                            val cacheFile = withContext(Dispatchers.IO) {
                                File(cacheDir, "temp_image.jpg").also { file ->
                                    try {
                                        responseBody.byteStream().use { input ->
                                            FileOutputStream(file).use { output ->
                                                input.copyTo(output)
                                            }
                                        }
                                    } catch (e: Exception) {
                                        Log.e("SelectPlayerActivity1", "Error saving image stream", e)
                                        file.delete()
                                        null
                                    }
                                }
                            }

                            if (cacheFile != null) {
                                val bitmap = withContext(Dispatchers.IO) {
                                    BitmapFactory.decodeFile(cacheFile.absolutePath)
                                }
                                withContext(Dispatchers.Main) {
                                    if (bitmap != null) {
                                        playerImageView.setImageBitmap(bitmap)
                                        cacheFile.delete()
                                    } else {
                                        Toast.makeText(this@SelectPlayerActivity1, "圖片解碼失敗", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            } else {
                                withContext(Dispatchers.Main) {
                                    Toast.makeText(this@SelectPlayerActivity1, "存檔失敗", Toast.LENGTH_SHORT).show()
                                }
                            }
                        } else {
                            Toast.makeText(this@SelectPlayerActivity1, "取得圖片資料失敗", Toast.LENGTH_SHORT).show()
                        }
                    } else {
                        Toast.makeText(this@SelectPlayerActivity1, "取得圖片失敗：${frameResponse.code()}", Toast.LENGTH_SHORT).show()
                    }
                } else {
                    Toast.makeText(this@SelectPlayerActivity1, "啟動分析失敗：${startResponse.code()}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(this@SelectPlayerActivity1, "發生錯誤，請稍後再試", Toast.LENGTH_SHORT).show()
                Log.e("SelectPlayerActivity", "Exception", e)
            }
        }
    }

    private fun startSharingWithAI(number: String) {
        Toast.makeText(this, "開始共享，背號：$number", Toast.LENGTH_LONG).show()
    }

    override fun onDestroy() {
        super.onDestroy()
        scope.cancel()
    }

    private fun convertViewRectToImage(rect: RectF): RectF? {
        val drawable = playerImageView.drawable ?: return null

        val matrix = playerImageView.imageMatrix
        val vals = FloatArray(9)
        matrix.getValues(vals)
        val scaleX = vals[Matrix.MSCALE_X]
        val scaleY = vals[Matrix.MSCALE_Y]
        val transX = vals[Matrix.MTRANS_X]
        val transY = vals[Matrix.MTRANS_Y]

        val drawableWidth = drawable.intrinsicWidth
        val drawableHeight = drawable.intrinsicHeight

        val left = (rect.left - transX) / scaleX
        val top = (rect.top - transY) / scaleY
        val right = (rect.right - transX) / scaleX
        val bottom = (rect.bottom - transY) / scaleY

        val imageLeft = left.coerceIn(0f, drawableWidth.toFloat())
        val imageTop = top.coerceIn(0f, drawableHeight.toFloat())
        val imageRight = right.coerceIn(0f, drawableWidth.toFloat())
        val imageBottom = bottom.coerceIn(0f, drawableHeight.toFloat())

        return RectF(imageLeft, imageTop, imageRight, imageBottom)
    }
}
