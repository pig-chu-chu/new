package com.example.feelwithus.ui.start

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.feelwithus.R
import com.example.feelwithus.data.model.LoginBody
import com.example.feelwithus.data.model.MyApp
import com.example.feelwithus.data.model.User
import com.example.feelwithus.data.network.RetrofitClientA
import com.example.feelwithus.data.network.RetrofitServiceA
import com.example.feelwithus.ui.main.MainActivity
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class StartActivity : AppCompatActivity() {

    private lateinit var usernameInput: EditText
    private lateinit var passwordInput: EditText
    private lateinit var btnLogin: Button
    private lateinit var txtSignup: TextView
    private lateinit var progressBar: ProgressBar
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_start)

        usernameInput = findViewById(R.id.username_input)
        passwordInput = findViewById(R.id.password_input)
        btnLogin = findViewById(R.id.btnLogin)
        txtSignup = findViewById(R.id.txt_signup)

        progressBar = findViewById(R.id.progressBar)

        btnLogin.setOnClickListener {
            val username = usernameInput.text.toString().trim()
            val password = passwordInput.text.toString().trim()
            Log.d("StartActivity", "username='$username', password='$password'")

            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "請輸入帳號與密碼", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            lifecycleScope.launch {
                try {
                    progressBar.visibility = View.VISIBLE   // 顯示 Loading
                    val response = RetrofitClientA.api.login(username, password)
                    progressBar.visibility = View.GONE      // 隱藏 Loading

                    if (response.isSuccessful) {
                        val body = response.body()
                        if (body != null && body.success == 1) {
                            val user = body.user ?: User(username = username)
                            Toast.makeText(this@StartActivity, "登入成功！", Toast.LENGTH_SHORT).show()
                            Log.d("StartActivity", "登入成功 user: $user")

                            // 儲存到 Application
                            val app = application as MyApp
                            app.currentUser = user

                            val intent = Intent(this@StartActivity, MainActivity::class.java)
                            startActivity(intent)
                            finish()
                        } else {
                            Toast.makeText(
                                this@StartActivity,
                                body?.message ?: "登入失敗",
                                Toast.LENGTH_SHORT
                            ).show()
                        }
                    } else {
                        Toast.makeText(this@StartActivity, "伺服器錯誤，請稍後再試", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    progressBar.visibility = View.GONE  // 異常時也要隱藏 Loading
                    Log.e("StartActivity", "登入失敗", e)
                    Toast.makeText(this@StartActivity, "無法連線，請檢查網路", Toast.LENGTH_SHORT).show()
                }
            }
        }

        txtSignup.setOnClickListener {
                startActivity(Intent(this, SignupActivity::class.java))
            }

    }
}