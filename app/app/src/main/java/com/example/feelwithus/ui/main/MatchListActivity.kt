package com.example.feelwithus.ui.main

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.ImageButton
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.feelwithus.R
import com.example.feelwithus.data.model.Match
import com.example.feelwithus.data.network.RetrofitClientA
import com.example.feelwithus.data.network.RetrofitClientC
import com.example.feelwithus.data.network.RetrofitClientD
import com.example.feelwithus.data.network.VideoNameRequest
import com.example.feelwithus.ui.auth.AnimatedVRActivity
import com.example.feelwithus.ui.auth.LiveVRActivity
import com.example.feelwithus.ui.auth.animatedOpActivity2
import com.example.feelwithus.ui.auth.liveOpActivity
import kotlinx.coroutines.launch
class MatchListActivity : AppCompatActivity() {
    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: MatchAdapter
    private val matchList = mutableListOf<Match>()
    private var categoryType: String = ""
    private lateinit var backbtn: ImageButton
    private lateinit var identification: ImageButton
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContentView(R.layout.activity_match_list)
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main)) { v, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }
        backbtn = findViewById(R.id.btnBack)
        identification = findViewById(R.id.identification)
        categoryType = intent.getStringExtra("categoryType") ?: "match_video"
        recyclerView = findViewById(R.id.recyclerViewMatches)
        recyclerView.layoutManager = LinearLayoutManager(this)
        adapter = MatchAdapter(matchList, categoryType) { match, mode ->
            lifecycleScope.launch {
                val videoNameRequest = getVideoNameRequest(match.fileName)
                Log.d("MatchList", "準備呼叫 dbStart，影片名稱: ${match.fileName}")
                try {
                    val responseC =  RetrofitClientC.api.dbStart(videoNameRequest)
                    Log.d("MatchList", "呼叫手套裝置 dbStart 回應: code=${responseC.code()} successBody=${responseC.body()?.success}")
                    val responseD = RetrofitClientD.api.dbStart(videoNameRequest)
                    Log.d("MatchList", "呼叫氣味裝置 dbStart 回應: code=${responseD.code()} successBody=${responseD.body()?.success}")
                    if (responseC.isSuccessful && responseC.body()?.success == true &&
                        responseD.isSuccessful && responseD.body()?.success == true){
                        val nextActivity = when (categoryType) {
                            "match_video" -> if (mode == "phone") liveOpActivity::class.java else LiveVRActivity::class.java
                            "animated_video" -> if (mode == "phone") animatedOpActivity2::class.java else AnimatedVRActivity::class.java
                            else -> null
                        }
                        if (nextActivity != null) {
                            Log.d("MatchList", "dbStart 成功，準備切換到下一個畫面: ${nextActivity.simpleName}")
                            val intent = Intent(this@MatchListActivity, nextActivity)
                            intent.putExtra("match_id", match.id)
                            intent.putExtra("match_title", match.fileName)
                            startActivity(intent)
                        }
                    } else {
                        Log.e("MatchList", "dbStart 呼叫失敗: 手套成功=${responseC.body()?.success}, 氣味成功=${responseD.body()?.success}")
                        Toast.makeText(this@MatchListActivity, "無法通知所有裝置開始播放，請稍後再試", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e("MatchList", "呼叫 dbStart 發生例外: ${e.message}")
                    Toast.makeText(this@MatchListActivity, "呼叫開始播放失敗：${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
        recyclerView.adapter = adapter
        fetchMatchList()
        if (categoryType == "match_video") {
            identification.visibility = ImageButton.VISIBLE
            identification.setOnClickListener {
                val intent = Intent(this, com.example.feelwithus.utils.SelectPlayerActivity1::class.java)
                //  應該會跳到一個頁面選"未被辨識的影片"，選擇後 傳被選的"影片名稱"給辨識ai並跳到 SelectPlayerActivity1
                //  等辨識ai接收"影片名稱" 回傳一楨影像 並開始框選
                //  框選後確認背號(或修改)並送出讓辨識api開始辨識，同時跳回 MatchListActivity-match_video 的影片列表
                //  如果辨識完成 那個新的辨識影片 加到列表供選擇體驗
                //  selectPlayerLauncher.launch(intent)
            }
        } else {
            identification.visibility = ImageButton.GONE
        }
        Log.d("MatchList", "RecyclerView visibility: ${recyclerView.visibility}")
        backbtn.setOnClickListener {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }
    private fun fetchMatchList() {
        lifecycleScope.launch {
            try {
                val response = when(categoryType) {
                    "match_video" -> RetrofitClientA.api.getMatchFootageList()
                    "animated_video" -> RetrofitClientA.api.get3DvideoList()
                    else -> RetrofitClientA.api.get3DvideoList()
                }
                if (response.isSuccessful && response.body() != null) {
                    Log.d("MatchList", "Response body: ${response.body()}")
                    matchList.clear()
                    matchList.addAll(response.body()!!)
                    adapter.notifyDataSetChanged()
                } else {
                    Log.e("MatchList", "Response failed: Code ${response.code()}, message: ${response.message()}")
                    Toast.makeText(this@MatchListActivity, "取得比賽失敗: ${response.message()}", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Log.e("MatchList", "Exception in fetch: ${e.message}")
                Toast.makeText(this@MatchListActivity, "取得出錯: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }
    private fun getVideoNameRequest(videoName: String): VideoNameRequest {
        return VideoNameRequest(videoName = videoName)
    }
}