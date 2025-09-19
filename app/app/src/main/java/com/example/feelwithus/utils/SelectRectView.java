package com.example.feelwithus.utils;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;

public class SelectRectView extends View {

    private float startX, startY, endX, endY;
    private boolean drawing = false;
    private Paint paint;

    public SelectRectView(Context context) {
        super(context);
        init();
    }

    public SelectRectView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    private void init() {
        paint = new Paint();
        paint.setColor(0x66FF0000); // 半透明紅色
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(5);
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (drawing) {
            RectF rect = new RectF(Math.min(startX, endX), Math.min(startY, endY),
                    Math.max(startX, endX), Math.max(startY, endY));
            canvas.drawRect(rect, paint);
        }
    }

    @Override
    public boolean onTouchEvent(MotionEvent event) {
        switch(event.getAction()) {
            case MotionEvent.ACTION_DOWN:
                startX = event.getX();
                startY = event.getY();
                endX = startX;
                endY = startY;
                drawing = true;
                invalidate();
                return true;
            case MotionEvent.ACTION_MOVE:
                endX = event.getX();
                endY = event.getY();
                invalidate();
                return true;
            case MotionEvent.ACTION_UP:
                endX = event.getX();
                endY = event.getY();
                invalidate();
                return true;
        }
        return super.onTouchEvent(event);
    }

    public RectF getSelectedRect() {
        if (!drawing) return null;
        return new RectF(Math.min(startX, endX), Math.min(startY, endY),
                Math.max(startX, endX), Math.max(startY, endY));
    }
}
