package com.example.feelwithus.data.network


import okhttp3.Interceptor
import okhttp3.Response
import okhttp3.Credentials

class BasicAuthInterceptor(user: String, password: String) : Interceptor {
    private val credentials: String = Credentials.basic(user, password)

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
            .newBuilder()
            .header("Authorization", credentials)
            .build()
        return chain.proceed(request)
    }
}