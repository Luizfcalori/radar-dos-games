package com.luizcalori.radartiktokhelper;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentValues;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String QUEUE_URL =
            "https://raw.githubusercontent.com/Luizfcalori/radar-dos-games/main/data/tiktok_queue.json";
    private static final String PREFS = "radar_tiktok_state";
    private static final String TIKTOK_PACKAGE = "com.zhiliaoapp.musically";
    private static final String PUBLIC_FOLDER = Environment.DIRECTORY_MOVIES + "/RadarTikTokHelper";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final ExecutorService imageExecutor = Executors.newSingleThreadExecutor();
    private final List<QueueItem> allItems = new ArrayList<>();
    private final List<QueueItem> visibleItems = new ArrayList<>();
    private final Map<String, Uri> downloaded = new HashMap<>();

    private TextView summary;
    private TextView titleLabel;
    private TextView statusChip;
    private TextView status;
    private ImageView thumbnail;
    private TextView thumbnailHint;
    private EditText caption;
    private Button copyButton;
    private Button shareButton;
    private Button previewButton;
    private Button downloadButton;
    private Button batchButton;
    private Button postedButton;
    private Button skipButton;
    private Button pendingFilter;
    private Button postedFilter;
    private Button allFilter;

    private QueueItem current;
    private int cursor = 0;
    private String filterMode = "pending";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        int pad = dp(16);
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(pad, pad, pad, pad);
        box.setBackgroundColor(Color.rgb(247, 247, 247));

        TextView appTitle = new TextView(this);
        appTitle.setText("Radar dos Games — TikTok");
        appTitle.setTextSize(25);
        appTitle.setTextColor(Color.rgb(20, 20, 20));
        box.addView(appTitle);

        TextView subtitle = new TextView(this);
        subtitle.setText("Shorts aprovados • legenda + hashtags prontas • publicação manual");
        subtitle.setTextSize(14);
        subtitle.setTextColor(Color.DKGRAY);
        subtitle.setPadding(0, dp(3), 0, dp(12));
        box.addView(subtitle);

        summary = new TextView(this);
        summary.setText("Carregando fila...");
        summary.setTextSize(15);
        summary.setTextColor(Color.rgb(55, 55, 55));
        summary.setPadding(dp(12), dp(10), dp(12), dp(10));
        summary.setBackgroundColor(Color.WHITE);
        box.addView(summary, fullWidth());

        Button syncButton = button("↻ Sincronizar Shorts aprovados");
        syncButton.setOnClickListener(v -> syncQueue(true));
        box.addView(syncButton);

        TextView filterTitle = section("FILTRO");
        box.addView(filterTitle);
        pendingFilter = button("Pendentes");
        postedFilter = button("Publicados");
        allFilter = button("Todos");
        pendingFilter.setOnClickListener(v -> setFilter("pending"));
        postedFilter.setOnClickListener(v -> setFilter("posted"));
        allFilter.setOnClickListener(v -> setFilter("all"));
        box.addView(threeButtonRow(pendingFilter, postedFilter, allFilter));

        TextView actionTitle = section("AÇÕES RÁPIDAS");
        box.addView(actionTitle);
        copyButton = button("📋 Copiar legenda");
        shareButton = button("▶ Enviar ao TikTok");
        copyButton.setOnClickListener(v -> copyCaption(true));
        shareButton.setOnClickListener(v -> shareCurrent());
        box.addView(actionRow(copyButton, shareButton));

        downloadButton = button("⬇ Baixar Short");
        batchButton = button("⬇ Baixar próximos 3");
        downloadButton.setOnClickListener(v -> downloadCurrent());
        batchButton.setOnClickListener(v -> downloadNextThree());
        box.addView(actionRow(downloadButton, batchButton));

        postedButton = button("✓ Publiquei");
        skipButton = button("↪ Próximo");
        postedButton.setOnClickListener(v -> markPosted());
        skipButton.setOnClickListener(v -> nextItem());
        box.addView(actionRow(postedButton, skipButton));

        TextView cardTitle = section("SHORT SELECIONADO");
        box.addView(cardTitle);

        thumbnail = new ImageView(this);
        thumbnail.setBackgroundColor(Color.rgb(225, 225, 225));
        thumbnail.setScaleType(ImageView.ScaleType.FIT_CENTER);
        box.addView(thumbnail, new LinearLayout.LayoutParams(-1, dp(320)));

        thumbnailHint = new TextView(this);
        thumbnailHint.setText("A prévia aparecerá aqui");
        thumbnailHint.setGravity(Gravity.CENTER);
        thumbnailHint.setTextColor(Color.GRAY);
        thumbnailHint.setPadding(0, dp(4), 0, dp(4));
        box.addView(thumbnailHint);

        previewButton = button("▶ Assistir prévia do vídeo");
        previewButton.setOnClickListener(v -> openPreview());
        box.addView(previewButton);

        titleLabel = new TextView(this);
        titleLabel.setText("Nenhum Short carregado");
        titleLabel.setTextSize(18);
        titleLabel.setTextColor(Color.BLACK);
        titleLabel.setPadding(0, dp(6), 0, dp(4));
        box.addView(titleLabel);

        statusChip = new TextView(this);
        statusChip.setText("AGUARDANDO");
        statusChip.setTextSize(12);
        statusChip.setTextColor(Color.rgb(90, 90, 90));
        statusChip.setPadding(dp(8), dp(5), dp(8), dp(5));
        statusChip.setBackgroundColor(Color.rgb(235, 235, 235));
        box.addView(statusChip);

        TextView captionTitle = new TextView(this);
        captionTitle.setText("Legenda + hashtags");
        captionTitle.setTextSize(15);
        captionTitle.setTextColor(Color.DKGRAY);
        captionTitle.setPadding(0, dp(10), 0, dp(4));
        box.addView(captionTitle);

        caption = new EditText(this);
        caption.setHint("A legenda pronta aparecerá aqui");
        caption.setMinLines(5);
        caption.setGravity(Gravity.TOP);
        caption.setBackgroundColor(Color.WHITE);
        caption.setPadding(dp(12), dp(10), dp(12), dp(10));
        box.addView(caption, fullWidth());

        status = new TextView(this);
        status.setText("Pronto.");
        status.setTextSize(14);
        status.setTextColor(Color.rgb(65, 65, 65));
        status.setPadding(0, dp(12), 0, dp(12));
        box.addView(status);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(box);
        setContentView(scroll);

        setControlsEnabled(false);
        syncQueue(false);
    }

    private LinearLayout.LayoutParams fullWidth() {
        return new LinearLayout.LayoutParams(-1, -2);
    }

    private TextView section(String text) {
        TextView v = new TextView(this);
        v.setText(text);
        v.setTextSize(13);
        v.setTextColor(Color.GRAY);
        v.setPadding(0, dp(10), 0, dp(4));
        return v;
    }

    private Button button(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(14);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, dp(4), 0, dp(4));
        b.setLayoutParams(p);
        return b;
    }

    private LinearLayout actionRow(Button left, Button right) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, -2, 1f);
        lp.setMargins(0, 0, dp(3), 0);
        LinearLayout.LayoutParams rp = new LinearLayout.LayoutParams(0, -2, 1f);
        rp.setMargins(dp(3), 0, 0, 0);
        row.addView(left, lp);
        row.addView(right, rp);
        return row;
    }

    private LinearLayout threeButtonRow(Button a, Button b, Button c) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        LinearLayout.LayoutParams p1 = new LinearLayout.LayoutParams(0, -2, 1f);
        p1.setMargins(0, 0, dp(2), 0);
        LinearLayout.LayoutParams p2 = new LinearLayout.LayoutParams(0, -2, 1f);
        p2.setMargins(dp(2), 0, dp(2), 0);
        LinearLayout.LayoutParams p3 = new LinearLayout.LayoutParams(0, -2, 1f);
        p3.setMargins(dp(2), 0, 0, 0);
        row.addView(a, p1);
        row.addView(b, p2);
        row.addView(c, p3);
        return row;
    }

    private void syncQueue(boolean toast) {
        status.setText("Sincronizando fila...");
        executor.execute(() -> {
            try {
                String json = readUrl(QUEUE_URL + "?ts=" + System.currentTimeMillis());
                JSONObject root = new JSONObject(json);
                JSONArray items = root.optJSONArray("items");
                List<QueueItem> loaded = new ArrayList<>();
                if (items != null) {
                    for (int i = 0; i < items.length(); i++) {
                        JSONObject o = items.optJSONObject(i);
                        if (o == null) continue;
                        QueueItem item = QueueItem.from(o);
                        if (item == null) continue;
                        if (!"approved".equalsIgnoreCase(item.status) && !"ready_for_tiktok".equalsIgnoreCase(item.status)) continue;
                        loaded.add(item);
                    }
                }
                runOnUiThread(() -> {
                    allItems.clear();
                    allItems.addAll(loaded);
                    cursor = 0;
                    rebuildVisibleItems();
                    status.setText("Fila sincronizada • " + loaded.size() + " aprovados.");
                    if (toast) Toast.makeText(this, "Fila atualizada.", Toast.LENGTH_SHORT).show();
                });
            } catch (Exception e) {
                runOnUiThread(() -> status.setText("Falha ao sincronizar: " + shortMessage(e)));
            }
        });
    }

    private void setFilter(String mode) {
        filterMode = mode;
        cursor = 0;
        rebuildVisibleItems();
    }

    private void rebuildVisibleItems() {
        Set<String> posted = getPostedIds();
        visibleItems.clear();
        for (QueueItem item : allItems) {
            boolean isPosted = posted.contains(item.id);
            if ("pending".equals(filterMode) && isPosted) continue;
            if ("posted".equals(filterMode) && !isPosted) continue;
            visibleItems.add(item);
        }
        updateFilterLabels(posted);
        if (visibleItems.isEmpty()) {
            current = null;
            clearCurrent();
        } else {
            if (cursor >= visibleItems.size()) cursor = 0;
            showCurrent();
        }
        updateSummary(posted);
    }

    private void updateFilterLabels(Set<String> posted) {
        int postedCount = 0;
        for (QueueItem item : allItems) if (posted.contains(item.id)) postedCount++;
        int pendingCount = Math.max(0, allItems.size() - postedCount);
        pendingFilter.setText(("pending".equals(filterMode) ? "✓ " : "") + "Pendentes (" + pendingCount + ")");
        postedFilter.setText(("posted".equals(filterMode) ? "✓ " : "") + "Publicados (" + postedCount + ")");
        allFilter.setText(("all".equals(filterMode) ? "✓ " : "") + "Todos (" + allItems.size() + ")");
    }

    private void updateSummary(Set<String> posted) {
        int postedCount = 0;
        for (QueueItem item : allItems) if (posted.contains(item.id)) postedCount++;
        int pendingCount = Math.max(0, allItems.size() - postedCount);
        summary.setText("Pendentes: " + pendingCount + "   •   Publicados: " + postedCount + "   •   Aprovados: " + allItems.size());
    }

    private void showCurrent() {
        if (visibleItems.isEmpty()) {
            clearCurrent();
            return;
        }
        current = visibleItems.get(cursor);
        titleLabel.setText(current.title);
        caption.setText(current.postText);
        boolean isPosted = getPostedIds().contains(current.id);
        statusChip.setText(isPosted ? "PUBLICADO" : "APROVADO • PENDENTE");
        statusChip.setBackgroundColor(isPosted ? Color.rgb(222, 245, 228) : Color.rgb(235, 235, 235));
        postedButton.setEnabled(!isPosted);
        setControlsEnabled(true);
        loadThumbnail(current);
    }

    private void clearCurrent() {
        titleLabel.setText("Nenhum Short neste filtro");
        caption.setText("");
        thumbnail.setImageDrawable(null);
        thumbnailHint.setText("Nenhum vídeo para exibir");
        statusChip.setText("SEM ITENS");
        setControlsEnabled(false);
    }

    private void setControlsEnabled(boolean enabled) {
        copyButton.setEnabled(enabled);
        shareButton.setEnabled(enabled);
        previewButton.setEnabled(enabled);
        downloadButton.setEnabled(enabled);
        batchButton.setEnabled(enabled);
        postedButton.setEnabled(enabled && current != null && !getPostedIds().contains(current.id));
        skipButton.setEnabled(enabled && visibleItems.size() > 1);
    }

    private void loadThumbnail(QueueItem item) {
        thumbnail.setImageDrawable(null);
        thumbnailHint.setText("Carregando prévia...");
        if (item.thumbnailUrl.isEmpty()) {
            thumbnailHint.setText("Sem miniatura; toque em Assistir prévia");
            return;
        }
        imageExecutor.execute(() -> {
            HttpURLConnection c = null;
            try {
                c = (HttpURLConnection) new URL(item.thumbnailUrl).openConnection();
                c.setConnectTimeout(12000);
                c.setReadTimeout(12000);
                c.setRequestProperty("User-Agent", "RadarTikTokHelper/1.0");
                try (InputStream in = new BufferedInputStream(c.getInputStream())) {
                    Bitmap bmp = BitmapFactory.decodeStream(in);
                    if (current != null && current.id.equals(item.id)) {
                        runOnUiThread(() -> {
                            thumbnail.setImageBitmap(bmp);
                            thumbnailHint.setText("Prévia rápida — o vídeo só abre quando você pedir");
                        });
                    }
                }
            } catch (Exception e) {
                if (current != null && current.id.equals(item.id)) {
                    runOnUiThread(() -> thumbnailHint.setText("Prévia indisponível; o vídeo pode ser aberto abaixo"));
                }
            } finally {
                if (c != null) c.disconnect();
            }
        });
    }

    private void openPreview() {
        if (current == null) return;
        Uri local = downloaded.get(current.id);
        Uri uri = local != null ? local : Uri.parse(current.mediaUrl);
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW);
            intent.setDataAndType(uri, "video/*");
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivity(intent);
        } catch (Exception e) {
            Toast.makeText(this, "Não encontrei um player para abrir a prévia.", Toast.LENGTH_LONG).show();
        }
    }

    private void copyCaption(boolean toast) {
        if (current == null) return;
        String text = caption.getText().toString().trim();
        ClipboardManager clipboard = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
        clipboard.setPrimaryClip(ClipData.newPlainText("Legenda TikTok", text));
        if (toast) Toast.makeText(this, "Legenda copiada.", Toast.LENGTH_SHORT).show();
    }

    private void downloadCurrent() {
        if (current == null) return;
        QueueItem item = current;
        status.setText("Baixando " + item.title + "...");
        downloadButton.setEnabled(false);
        executor.execute(() -> {
            try {
                Uri uri = downloadItem(item);
                downloaded.put(item.id, uri);
                runOnUiThread(() -> {
                    status.setText("Short salvo em Movies/RadarTikTokHelper.");
                    downloadButton.setEnabled(true);
                    Toast.makeText(this, "Download concluído.", Toast.LENGTH_SHORT).show();
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    status.setText("Falha no download: " + shortMessage(e));
                    downloadButton.setEnabled(true);
                });
            }
        });
    }

    private void downloadNextThree() {
        if (current == null || visibleItems.isEmpty()) return;
        List<QueueItem> batch = new ArrayList<>();
        int count = Math.min(3, visibleItems.size());
        for (int i = 0; i < count; i++) {
            batch.add(visibleItems.get((cursor + i) % visibleItems.size()));
        }
        status.setText("Baixando " + batch.size() + " Shorts...");
        batchButton.setEnabled(false);
        executor.execute(() -> {
            int ok = 0;
            for (QueueItem item : batch) {
                try {
                    Uri uri = downloadItem(item);
                    downloaded.put(item.id, uri);
                    ok++;
                } catch (Exception ignored) {
                }
            }
            int done = ok;
            runOnUiThread(() -> {
                batchButton.setEnabled(true);
                status.setText(done + " de " + batch.size() + " Shorts baixados.");
                Toast.makeText(this, done + " Shorts prontos no celular.", Toast.LENGTH_SHORT).show();
            });
        });
    }

    private Uri downloadItem(QueueItem item) throws Exception {
        if (downloaded.containsKey(item.id)) return downloaded.get(item.id);
        HttpURLConnection c = (HttpURLConnection) new URL(item.mediaUrl).openConnection();
        c.setConnectTimeout(20000);
        c.setReadTimeout(60000);
        c.setRequestProperty("User-Agent", "RadarTikTokHelper/1.0");
        c.setInstanceFollowRedirects(true);
        c.connect();
        if (c.getResponseCode() < 200 || c.getResponseCode() >= 300) {
            throw new IllegalStateException("HTTP " + c.getResponseCode());
        }

        String fileName = sanitize(item.id + "_" + item.title) + ".mp4";
        ContentValues values = new ContentValues();
        values.put(MediaStore.Video.Media.DISPLAY_NAME, fileName);
        values.put(MediaStore.Video.Media.MIME_TYPE, "video/mp4");
        values.put(MediaStore.Video.Media.RELATIVE_PATH, PUBLIC_FOLDER);
        values.put(MediaStore.Video.Media.IS_PENDING, 1);

        Uri uri = getContentResolver().insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, values);
        if (uri == null) throw new IllegalStateException("Não foi possível criar o arquivo");
        try (InputStream in = new BufferedInputStream(c.getInputStream());
             OutputStream out = getContentResolver().openOutputStream(uri)) {
            if (out == null) throw new IllegalStateException("Sem acesso ao arquivo");
            byte[] buffer = new byte[1024 * 128];
            int n;
            while ((n = in.read(buffer)) != -1) out.write(buffer, 0, n);
            out.flush();
        } catch (Exception e) {
            getContentResolver().delete(uri, null, null);
            throw e;
        } finally {
            c.disconnect();
        }
        ContentValues ready = new ContentValues();
        ready.put(MediaStore.Video.Media.IS_PENDING, 0);
        getContentResolver().update(uri, ready, null, null);
        return uri;
    }

    private void shareCurrent() {
        if (current == null) return;
        QueueItem item = current;
        copyCaption(false);
        Uri uri = downloaded.get(item.id);
        if (uri != null) {
            sendToTikTok(uri);
            return;
        }
        status.setText("Preparando Short para o TikTok...");
        shareButton.setEnabled(false);
        executor.execute(() -> {
            try {
                Uri saved = downloadItem(item);
                downloaded.put(item.id, saved);
                runOnUiThread(() -> {
                    shareButton.setEnabled(true);
                    status.setText("Legenda copiada. Finalize a publicação no TikTok.");
                    sendToTikTok(saved);
                });
            } catch (Exception e) {
                runOnUiThread(() -> {
                    shareButton.setEnabled(true);
                    status.setText("Falha ao preparar vídeo: " + shortMessage(e));
                });
            }
        });
    }

    private void sendToTikTok(Uri uri) {
        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setType("video/*");
        intent.putExtra(Intent.EXTRA_STREAM, uri);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            getPackageManager().getPackageInfo(TIKTOK_PACKAGE, 0);
            intent.setPackage(TIKTOK_PACKAGE);
            startActivity(intent);
        } catch (Exception e) {
            intent.setPackage(null);
            startActivity(Intent.createChooser(intent, "Publicar Short"));
        }
    }

    private void markPosted() {
        if (current == null) return;
        Set<String> posted = getPostedIds();
        posted.add(current.id);
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putStringSet("posted_ids", new HashSet<>(posted)).apply();
        Uri uri = downloaded.remove(current.id);
        if (uri != null) {
            try { getContentResolver().delete(uri, null, null); } catch (Exception ignored) {}
        }
        status.setText("Marcado como publicado. O próximo pendente foi carregado.");
        cursor = 0;
        rebuildVisibleItems();
    }

    private void nextItem() {
        if (visibleItems.isEmpty()) return;
        cursor = (cursor + 1) % visibleItems.size();
        showCurrent();
    }

    private Set<String> getPostedIds() {
        Set<String> ids = getSharedPreferences(PREFS, MODE_PRIVATE).getStringSet("posted_ids", null);
        return ids == null ? new HashSet<>() : new HashSet<>(ids);
    }

    private String readUrl(String url) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(12000);
        c.setReadTimeout(12000);
        c.setRequestProperty("User-Agent", "RadarTikTokHelper/1.1");
        c.setRequestProperty("Cache-Control", "no-cache, no-store, max-age=0");
        c.setRequestProperty("Pragma", "no-cache");
        c.setUseCaches(false);
        try {
            int code = c.getResponseCode();
            if (code < 200 || code >= 300) throw new IllegalStateException("HTTP " + code);
            StringBuilder sb = new StringBuilder();
            try (BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = r.readLine()) != null) sb.append(line).append('\n');
            }
            return sb.toString();
        } finally {
            c.disconnect();
        }
    }

    private String sanitize(String s) {
        String out = s.replaceAll("[^a-zA-Z0-9._-]+", "_");
        if (out.length() > 80) out = out.substring(0, 80);
        return out;
    }

    private String shortMessage(Exception e) {
        String m = e.getMessage();
        return m == null || m.trim().isEmpty() ? e.getClass().getSimpleName() : m;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static class QueueItem {
        final String id;
        final String title;
        final String mediaUrl;
        final String thumbnailUrl;
        final String postText;
        final String status;

        QueueItem(String id, String title, String mediaUrl, String thumbnailUrl, String postText, String status) {
            this.id = id;
            this.title = title;
            this.mediaUrl = mediaUrl;
            this.thumbnailUrl = thumbnailUrl;
            this.postText = postText;
            this.status = status;
        }

        static QueueItem from(JSONObject o) {
            String id = o.optString("id", o.optString("video_id", "")).trim();
            String title = o.optString("title", "Short Radar dos Games").trim();
            String media = o.optString("media_url", "").trim();
            String thumb = o.optString("thumbnail_url", "").trim();
            String post = o.optString("post_text", "").trim();
            String status = o.optString("status", "approved").trim().toLowerCase(Locale.ROOT);
            if (id.isEmpty() || media.isEmpty()) return null;
            return new QueueItem(id, title.isEmpty() ? "Short Radar dos Games" : title, media, thumb, post, status);
        }
    }
}
