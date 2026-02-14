# Brand Logos

This directory contains brand logos for platforms and LLM providers used in the Content Remix Agent.

## Downloaded Logos

Successfully downloaded logos:
- ✅ `xhs.png` - 小红书 (Xiaohongshu) - 32x32
- ✅ `dy.png` - 抖音 (Douyin) - 32x32
- ✅ `ks.png` - 快手 (Kuaishou) - 32x32
- ✅ `anthropic.png` - Anthropic - 48x48
- ✅ `deepseek.png` - DeepSeek - 128x128

## Missing Logos (Require Manual Download)

The following logos failed automated download and need to be added manually:

### Bilibili (bili.png)
- Search: [Google Images - bilibili logo official transparent](https://www.google.com/search?tbm=isch&q=bilibili+logo+official+transparent)
- Target size: 128x128 PNG with transparent background
- Save as: `bili.png`

### OpenAI (openai.png)
- Search: [Google Images - openai logo official transparent](https://www.google.com/search?tbm=isch&q=openai+logo+official+transparent)
- Target size: 128x128 PNG with transparent background
- Save as: `openai.png`

## Logo Requirements

- **Format:** PNG with transparent background
- **Size:** 128x128 pixels (will be auto-resized if needed)
- **Max file size:** 500KB
- **Naming:** `{brand_key}.png` (lowercase)

## Automated Download

To download or update logos automatically:

```bash
# Download all logos
cd content_remix_agent/backend
uv run python scripts/download_brand_logos.py

# Force re-download (overwrite existing)
uv run python scripts/download_brand_logos.py --force

# Download specific brand
uv run python scripts/download_brand_logos.py --brand xhs --force

# Download by category
uv run python scripts/download_brand_logos.py --category platform
uv run python scripts/download_brand_logos.py --category llm_provider

# Preview without downloading
uv run python scripts/download_brand_logos.py --dry-run
```

## Frontend Integration

Logos are automatically used in:
- **Settings > Cookies Manager** - Platform logos
- **Settings > LLM Config Manager** - LLM provider logos

Frontend will automatically fall back to Material Symbols icons if logos fail to load.

## API Access

Logos are served via FastAPI static files:
- URL: `http://localhost:8001/assets/logos/{brand_key}.png`
- Example: `http://localhost:8001/assets/logos/xhs.png`

## Manual Optimization

If you manually download a logo, optimize it using:

```bash
cd content_remix_agent/backend
uv run python -c "
from PIL import Image
from pathlib import Path
img = Image.open('assets/logos/your_logo.png')
if img.mode != 'RGBA':
    img = img.convert('RGBA')
img.thumbnail((128, 128))
img.save('assets/logos/your_logo.png', format='PNG', optimize=True)
print(f'Optimized: {img.size}, {Path(\"assets/logos/your_logo.png\").stat().st_size} bytes')
"
```

## Troubleshooting

**Logo not displaying in frontend:**
1. Check file exists: `ls -l content_remix_agent/backend/assets/logos/`
2. Verify file format: `file content_remix_agent/backend/assets/logos/*.png`
3. Check backend is serving static files (FastAPI should be running)
4. Open browser console for 404 errors
5. Fallback icon should appear if logo fails

**Download script fails:**
- Some websites block automated downloads (403/412 errors)
- Fallback to manual download following links above
- Ensure `httpx` and `pillow` packages are installed
