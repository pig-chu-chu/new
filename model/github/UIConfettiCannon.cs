using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

public class UIConfettiCannon : MonoBehaviour
{
    // ───────────────────────── Layer / Sprite ─────────────────────────
    [Header("Layer / Sprites")]
    public RectTransform layer;       // 建議指向自己（Reset 會自動抓）
    public Sprite[] sprites;          // 可放多個彩紙圖；留空會用 1x1 白色方塊

    // ───────────────────────── 顏色 ─────────────────────────
    [Header("Colors")]
    public Color[] palette = new Color[] {
        new Color(1f,0.3f,0.3f),  // 紅
        new Color(1f,0.6f,0.2f),  // 橙
        new Color(1f,0.9f,0.2f),  // 黃
        new Color(0.2f,0.8f,0.4f),// 綠
        new Color(0.2f,0.7f,1f),  // 藍
        new Color(0.8f,0.4f,1f)   // 紫
    };

    // ───────────────────────── 發射設定 ─────────────────────────
    [Header("Emission")]
    public int piecesPerBurst = 160;  // 每次爆幾片
    public int burstCount = 3;        // 連續爆幾次
    public float burstInterval = 0.15f;
    public bool bothSides = true;     // 左右各一邊

    // ───────────────────────── 運動參數（px/sec） ─────────────────────────
    [Header("Motion (pixels/sec)")]
    public Vector2 speedRange = new Vector2(600f, 900f);
    public float spreadAngle = 28f;         // 夾角 ±度數
    public float gravity = -1200f;          // 向下加速度(px/s^2)
    public Vector2 sizeRange = new Vector2(8f, 14f);
    public Vector2 spinRange = new Vector2(-360f, 360f); // 角速度(度/秒)

    // ───────────────────────── 生命期 ─────────────────────────
    [Header("Lifetime")]
    public float lifetime = 3.0f;     // 存在多久
    public float fadeOut = 0.6f;      // 最後淡出秒數

    // ───────────────────────── 兩段式音效 ─────────────────────────
    [Header("Audio (兩段式)")]
    public AudioSource audioSource;   // 指到常駐的 SFXPlayer（2D、啟用）
    public AudioClip sfx1;            // 例：砰(pop)
    public float sfx1Volume = 1f;
    public AudioClip sfx2;            // 例：歡呼(cheer)
    public float sfx2Volume = 1f;
    // 若 >=0 用固定間隔；若 <0 自動等到 sfx1.length 再播 sfx2
    public float gapAfterFirst = -1f;

    // ───────────────────────── 內部/共用 ─────────────────────────
    static Sprite _fallbackSprite;    // sprites 為空時使用
    static Sprite FallbackSprite()
    {
        if (_fallbackSprite) return _fallbackSprite;
        var tex = new Texture2D(1, 1, TextureFormat.RGBA32, false);
        tex.SetPixel(0, 0, Color.white);
        tex.Apply();
        _fallbackSprite = Sprite.Create(tex, new Rect(0, 0, 1, 1), new Vector2(0.5f, 0.5f), 100f);
        return _fallbackSprite;
    }

    void Reset()
    {
        layer = GetComponent<RectTransform>();
    }

    // 在 Timeline 的 Signal 呼叫這個
    public void Fire()
    {
        StartCoroutine(PlaySfxSequence()); // 先播音效①→（等/間隔）→音效②
        StartCoroutine(FireRoutine());     // 同步噴彩炮
    }

    // 兩段式音效
    IEnumerator PlaySfxSequence()
    {
        Vector3 pos = Camera.main ? Camera.main.transform.position : Vector3.zero;

        // 播第一段
        if (sfx1)
        {
            if (audioSource && audioSource.enabled && audioSource.gameObject.activeInHierarchy)
                audioSource.PlayOneShot(sfx1, sfx1Volume);
            else
                AudioSource.PlayClipAtPoint(sfx1, pos, sfx1Volume);
        }

        // 等待：固定間隔 or 依 sfx1 長度
        float wait = 0f;
        if (gapAfterFirst >= 0f) wait = gapAfterFirst;
        else if (sfx1)           wait = sfx1.length / Mathf.Max(0.01f, (audioSource ? audioSource.pitch : 1f));
        if (wait > 0f) yield return new WaitForSecondsRealtime(wait);

        // 播第二段
        if (sfx2)
        {
            if (audioSource && audioSource.enabled && audioSource.gameObject.activeInHierarchy)
                audioSource.PlayOneShot(sfx2, sfx2Volume);
            else
                AudioSource.PlayClipAtPoint(sfx2, pos, sfx2Volume);
        }
    }

    // 彩炮流程（非 timeScale，錄影/慢動作也正確）
    IEnumerator FireRoutine()
    {
        var rt = layer ? layer : (RectTransform)transform;
        var rect = rt.rect;

        // 左右兩個噴發原點（相對畫面中心）
        Vector2 leftOrigin  = new Vector2(-rect.width * 0.45f,  rect.height * 0.25f);
        Vector2 rightOrigin = new Vector2( rect.width * 0.45f,  rect.height * 0.25f);

        for (int b = 0; b < burstCount; b++)
        {
            SpawnBurst(leftOrigin,  true);
            if (bothSides) SpawnBurst(rightOrigin, false);
            if (burstInterval > 0f) yield return new WaitForSecondsRealtime(burstInterval);
        }
    }

    void SpawnBurst(Vector2 origin, bool fromLeft)
    {
        for (int i = 0; i < piecesPerBurst; i++)
        {
            // 方向：朝畫面中心，加一點散射角
            Vector2 toCenter = (-origin).normalized;
            float jitter = Random.Range(-spreadAngle, spreadAngle);
            Vector2 dir = Rotate(toCenter, jitter * Mathf.Deg2Rad);

            float speed = Random.Range(speedRange.x, speedRange.y);
            Vector2 vel = dir * speed;

            // 生成 UI 片
            var go = new GameObject("Confetti", typeof(RectTransform), typeof(Image));
            var rt = go.GetComponent<RectTransform>();
            rt.SetParent(layer ? layer : (RectTransform)transform, false);
            rt.anchoredPosition = origin + new Vector2(Random.Range(-18f, 18f), Random.Range(-18f, 18f));
            rt.localRotation = Quaternion.Euler(0, 0, Random.Range(0f, 360f));
            rt.sizeDelta = Vector2.one * Random.Range(sizeRange.x, sizeRange.y);

            var img = go.GetComponent<Image>();
            img.sprite = (sprites != null && sprites.Length > 0)
                         ? sprites[Random.Range(0, sprites.Length)]
                         : FallbackSprite();
            img.type = Image.Type.Simple;
            var col = palette[Random.Range(0, palette.Length)];
            col.a = 1f;
            img.color = col;

            float angVel = Random.Range(spinRange.x, spinRange.y);
            go.AddComponent<MonoLife>().Run(lifetime, fadeOut, vel, gravity, angVel);
        }
    }

    static Vector2 Rotate(Vector2 v, float rad)
    {
        float c = Mathf.Cos(rad), s = Mathf.Sin(rad);
        return new Vector2(c * v.x - s * v.y, s * v.x + c * v.y);
    }

    // 小型內嵌行為：移動＋旋轉＋淡出＋銷毀（使用 unscaledDeltaTime）
    private class MonoLife : MonoBehaviour
    {
        RectTransform rt; Image img;
        Vector2 vel; float g; float angVel; float life; float fade;

        public void Run(float lifetime, float fadeOut, Vector2 v0, float gravity, float angV)
        {
            rt = GetComponent<RectTransform>();
            img = GetComponent<Image>();
            vel = v0; g = gravity; angVel = angV; life = lifetime; fade = fadeOut;
            StartCoroutine(Co());
        }

        IEnumerator Co()
        {
            float t = 0f;
            var baseCol = img.color;

            // 存在期
            while (t < life - fade)
            {
                float dt = Time.unscaledDeltaTime;
                t += dt;
                vel.y += g * dt;
                rt.anchoredPosition += vel * dt;
                rt.Rotate(0, 0, angVel * dt);
                yield return null;
            }

            // 淡出期
            float f = 0f;
            while (f < fade)
            {
                float dt = Time.unscaledDeltaTime;
                f += dt;
                vel.y += g * dt;
                rt.anchoredPosition += vel * dt;
                rt.Rotate(0, 0, angVel * dt);

                var c = baseCol; c.a = Mathf.Lerp(1f, 0f, Mathf.Clamp01(f / fade));
                img.color = c;
                yield return null;
            }

            Destroy(gameObject);
        }
    }

    // 右鍵元件選單 → 可在 Play 模式直接測試
    [ContextMenu("Test Fire")]
    void TestFire()
    {
        Fire();
    }
}
