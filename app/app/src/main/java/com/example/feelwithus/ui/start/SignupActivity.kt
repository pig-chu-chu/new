package com.example.feelwithus.ui.start

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.feelwithus.R
import com.example.feelwithus.data.model.RegisterBody
import com.example.feelwithus.data.network.RetrofitClientA
import com.example.feelwithus.data.network.RetrofitServiceA
import kotlinx.coroutines.launch

class SignupActivity : AppCompatActivity() {

    private lateinit var usernameSignup: EditText
    private lateinit var passwordSignup: EditText
    private lateinit var btnRegister: Button
    private lateinit var backbtn: ImageButton

    private val retrofitService: RetrofitServiceA by lazy {
        RetrofitClientA.api
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_signup)

        usernameSignup = findViewById(R.id.username_signup)
        passwordSignup = findViewById(R.id.password_signup)
        btnRegister = findViewById(R.id.btnRegister)
        backbtn = findViewById(R.id.btnBack)

        btnRegister.setOnClickListener {
            val username = usernameSignup.text.toString().trim()
            val password = passwordSignup.text.toString().trim()

            if (username.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "請填寫帳號與密碼", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val registerBody = RegisterBody(username = username, password = password)

            // 使用 Coroutine 呼叫 Retrofit
            lifecycleScope.launch {
                try {
                    val response = RetrofitClientA.api.register(username, password )

                    if (response.isSuccessful && response.body()?.success == 1) {
                        Toast.makeText(this@SignupActivity, "註冊成功，請登入！", Toast.LENGTH_SHORT).show()
                        startActivity(Intent(this@SignupActivity, StartActivity::class.java))
                        finish()
                    } else {
                        Toast.makeText(this@SignupActivity, response.body()?.message ?: "註冊失敗", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Log.e("SignupActivity", "註冊失敗", e)
                    Toast.makeText(this@SignupActivity, "伺服器錯誤或網路異常", Toast.LENGTH_SHORT).show()
                }
            }
        }

        backbtn.setOnClickListener {
            startActivity(Intent(this, StartActivity::class.java))
            finish()
        }
    }
}
