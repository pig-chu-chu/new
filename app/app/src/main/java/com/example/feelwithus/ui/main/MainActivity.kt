package com.example.feelwithus.ui.main

import android.content.Intent
import android.os.Bundle
import android.util.Log
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import android.widget.Button
import android.widget.ImageButton
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import com.example.feelwithus.R
import com.example.feelwithus.data.model.MyApp
import com.example.feelwithus.data.model.User
import com.example.feelwithus.ui.start.StartActivity

class MainActivity : AppCompatActivity() {

    private lateinit var tvWelcome: TextView
    private lateinit var btnMatchVideo: Button
    private lateinit var btnAnimatedVideo: Button
    private lateinit var backbtn: ImageButton

    private val app get() = application as MyApp
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_main)

        tvWelcome = findViewById(R.id.tvWelcome)
        btnMatchVideo = findViewById(R.id.btnMatchVideo)
        btnAnimatedVideo = findViewById(R.id.btnAnimatedVideo)
        backbtn = findViewById(R.id.btnBack)


        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        val user = app.currentUser
        Log.d("MainActivity", "收到 user: $user")
        tvWelcome.text = "歡迎，${user?.username ?: "使用者"}"


        btnMatchVideo.setOnClickListener {
            goToMatchList("match_video")
        }
        btnAnimatedVideo.setOnClickListener {
            goToMatchList("animated_video")
        }

        backbtn.setOnClickListener {
            AlertDialog.Builder(this)
                .setTitle("登出確認")
                .setMessage("你確定要登出嗎？")
                .setPositiveButton("確定") { _, _ ->
                    startActivity(Intent(this, StartActivity::class.java))
                    finish()
                }
                .setNegativeButton("取消", null)
                .show()
        }
    }
    private fun goToMatchList(categoryType: String) {
        val intent = Intent(this, MatchListActivity::class.java)
        intent.putExtra("categoryType", categoryType)
        startActivity(intent)
    }
}
