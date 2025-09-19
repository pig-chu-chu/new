package com.example.feelwithus.ui.main

import android.graphics.Color
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.example.feelwithus.R
import com.example.feelwithus.data.model.Match

class MatchAdapter(
    private val matches: List<Match>,
    private val categoryType: String,
    private val onViewSelected: (Match, String) -> Unit
) : RecyclerView.Adapter<MatchAdapter.MatchViewHolder>() {

    private var selectedPos = RecyclerView.NO_POSITION

    inner class MatchViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val title: TextView = view.findViewById(R.id.matchTitle)
        val date: TextView = view.findViewById(R.id.matchDate)
        val watchLayout: View = view.findViewById(R.id.watchLayout)
        val btnMobile: Button = view.findViewById(R.id.btnMobile)
        val btnVR: Button = view.findViewById(R.id.btnVR)

        init {
            view.setOnClickListener {
                val prev = selectedPos
                selectedPos = adapterPosition
                notifyItemChanged(prev)
                notifyItemChanged(selectedPos)
            }
            btnMobile.setOnClickListener {
                val pos = adapterPosition
                if (pos != RecyclerView.NO_POSITION) {
                    onViewSelected(matches[pos], "phone")
                }
            }
            btnVR.setOnClickListener {
                val pos = adapterPosition
                if (pos != RecyclerView.NO_POSITION) {
                    onViewSelected(matches[pos], "vr")
                }
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): MatchViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_match, parent, false)
        return MatchViewHolder(view)
    }

    override fun onBindViewHolder(holder: MatchViewHolder, position: Int) {
        val match = matches[position]
        holder.title.text = match.fileName
        holder.date.text = match.uploadTime
        holder.watchLayout.visibility = if (position == selectedPos) View.VISIBLE else View.GONE
        holder.itemView.setBackgroundColor(if (position == selectedPos) Color.LTGRAY else Color.WHITE)
    }

    override fun getItemCount(): Int = matches.size
}
