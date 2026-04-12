#!/usr/bin/env bash
# clean.sh — Limpia outputs entre pruebas del pipeline.
#
# Uso:
#   bash clean.sh          → borra clips, candidatos y subtítulos (conserva transcript)
#   bash clean.sh --full   → borra todo incluyendo transcript y audio WAV

set -euo pipefail

CACHE_DIR="${CACHE_DIR:-cache}"
OUTPUT_DIR="${OUTPUT_DIR:-output}"

if [[ "${1:-}" == "--full" ]]; then
    echo "🗑️  Limpieza COMPLETA (incluyendo transcripción y audio)..."
    rm -f "$CACHE_DIR/transcript.json"
    rm -f "$CACHE_DIR/audio.wav"
fi

echo "🗑️  Borrando candidatos, clips y subtítulos..."
rm -f "$CACHE_DIR/candidates.json"
rm -f "$CACHE_DIR/validated.json"
rm -f "$CACHE_DIR/clip_"*.ass   2>/dev/null || true
rm -f "$OUTPUT_DIR/"*.mp4       2>/dev/null || true
rm -f "$CACHE_DIR/clips/"*.mp4  2>/dev/null || true

echo ""
echo "✅ Limpieza completada."

if [[ "${1:-}" != "--full" ]]; then
    if [[ -f "$CACHE_DIR/transcript.json" ]]; then
        SIZE=$(du -sh "$CACHE_DIR/transcript.json" | cut -f1)
        echo "   📝 Transcripción conservada ($SIZE) — listo para volver a procesar."
    fi
fi
echo ""
echo "📁 Estado actual de $CACHE_DIR:"
ls -lh "$CACHE_DIR/" 2>/dev/null || echo "   (vacío)"
echo ""
echo "📁 Estado actual de $OUTPUT_DIR:"
ls -lh "$OUTPUT_DIR/" 2>/dev/null || echo "   (vacío)"
