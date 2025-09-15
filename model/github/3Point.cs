using UnityEngine;

public class CourtLinesFIBA : MonoBehaviour
{
    [Header("線條設定")]
    public Material lineMaterial;
    public float lineWidth = 0.05f;
    public float yOffset = 0.01f;

    [Header("場地尺寸 (FIBA標準)")]
    public float courtLength = 28f;
    public float courtWidth = 15f;

    [Header("籃框物件")]
    public GameObject rightHoop; // 右側籃框
    public GameObject leftHoop;  // 左側籃框

    void Start()
    {
        AlignHoopsToCourt(); // 自動對齊籃框
        ClearExistingLines();
        DrawAllLines();
    }

    void AlignHoopsToCourt()
    {
        float hoopZ = courtLength / 2f - 1.575f;
        
        // 右側籃框 (負Z方向)
        if (rightHoop != null)
        {
            Vector3 pos = rightHoop.transform.position;
            pos.z = -hoopZ;
            rightHoop.transform.position = pos;
        }

        // 左側籃框 (正Z方向)
        if (leftHoop != null)
        {
            Vector3 pos = leftHoop.transform.position;
            pos.z = hoopZ;
            leftHoop.transform.position = pos;
        }
    }

    void DrawAllLines()
    {
        DrawSidelines();
        DrawCenterCircle();
        DrawThreePointArc(1);  // 上半場
        DrawThreePointArc(-1); // 下半場
        DrawPaintArea(1);
        DrawPaintArea(-1);
    }

    void DrawSidelines()
    {
        float w = courtWidth / 2f;
        float l = courtLength / 2f;

        CreateLine("Sideline_Left", new Vector3(-w, yOffset, -l), new Vector3(-w, yOffset, l));
        CreateLine("Sideline_Right", new Vector3(w, yOffset, -l), new Vector3(w, yOffset, l));
        CreateLine("Baseline_Back", new Vector3(-w, yOffset, -l), new Vector3(w, yOffset, -l));
        CreateLine("Baseline_Front", new Vector3(-w, yOffset, l), new Vector3(w, yOffset, l));
        CreateLine("CenterLine", new Vector3(-w, yOffset, 0), new Vector3(w, yOffset, 0));
    }

    void DrawCenterCircle()
    {
        DrawCircle("CenterCircle", new Vector3(0, yOffset, 0), 1.8f, 0, 360);
    }

    void DrawThreePointArc(int direction)
{
    float hoopZ = direction * (courtLength / 2f - 1.575f);
    Vector3 center = new Vector3(0, yOffset, hoopZ);

    // 計算新的半徑，使弧端剛好在邊線
    float arcEndX = courtWidth / 2f;
    float radius = Mathf.Sqrt(arcEndX * arcEndX + (hoopZ - direction * (courtLength / 2f)) * (hoopZ - direction * (courtLength / 2f)));

    // 弧線角度範圍
    float startAngle = direction > 0 ? 270 - 90 : 90 - 90; // -90度
    float endAngle = direction > 0 ? 270 + 90 : 90 + 90;   // +90度

    DrawCircle($"ThreePointArc_{(direction > 0 ? "Top" : "Bottom")}", center, radius, startAngle, endAngle);
}

    void DrawPaintArea(int direction)
    {
        float width = 4.9f;
        float height = 5.8f;
        float baseZ = direction * (courtLength / 2f); // 底線Z座標
        float freeThrowLineZ = baseZ - direction * height;

        // 罰球區矩形
        Vector3 bl = new Vector3(-width/2f, yOffset, baseZ);
        Vector3 br = new Vector3(width/2f, yOffset, baseZ);
        Vector3 tl = new Vector3(-width/2f, yOffset, freeThrowLineZ);
        Vector3 tr = new Vector3(width/2f, yOffset, freeThrowLineZ);

        CreateLine($"PaintLeft_{direction}", bl, tl);
        CreateLine($"PaintRight_{direction}", br, tr);
        CreateLine($"FreeThrowLine_{direction}", tl, tr);

        // 罰球圈
        float startAngle = direction > 0 ? 180 : 0;
        float endAngle = direction > 0 ? 360 : 180;
        DrawCircle($"FreeThrowArc_{direction}", new Vector3(0, yOffset, freeThrowLineZ), 1.8f, startAngle, endAngle);
    }

    void CreateLine(string name, Vector3 start, Vector3 end)
    {
        GameObject line = new GameObject(name);
        line.transform.parent = transform;
        LineRenderer lr = line.AddComponent<LineRenderer>();
        lr.useWorldSpace = true;
        lr.positionCount = 2;
        lr.SetPositions(new Vector3[]{start, end});
        lr.material = lineMaterial;
        lr.startWidth = lineWidth;
        lr.endWidth = lineWidth;
    }

    void DrawCircle(string name, Vector3 center, float radius, float angleStart, float angleEnd, int segments = 60)
    {
        GameObject circle = new GameObject(name);
        circle.transform.parent = transform;
        LineRenderer lr = circle.AddComponent<LineRenderer>();
        lr.useWorldSpace = true;
        lr.positionCount = segments + 1;
        lr.material = lineMaterial;
        lr.startWidth = lineWidth;
        lr.endWidth = lineWidth;

        for (int i = 0; i <= segments; i++)
        {
            float angle = Mathf.Deg2Rad * Mathf.Lerp(angleStart, angleEnd, i / (float)segments);
            float x = Mathf.Cos(angle) * radius;
            float z = Mathf.Sin(angle) * radius;
            lr.SetPosition(i, center + new Vector3(x, 0, z));
        }
    }

    void ClearExistingLines()
    {
        for (int i = transform.childCount - 1; i >= 0; i--)
        {
            DestroyImmediate(transform.GetChild(i).gameObject);
        }
    }
}

