#!/usr/bin/env bash
# =============================================================
# maplebot 打包脚本
# 用法：bash pack.sh [版本号]
# 示例：bash pack.sh 1.0.0
# =============================================================
set -euo pipefail

VERSION="${1:-$(date +%Y%m%d%H%M%S)}"
PACKAGE_NAME="maplebot"
DIST_DIR="dist"
OUTPUT="${DIST_DIR}/${PACKAGE_NAME}-${VERSION}.tar.gz"

echo "==> 打包版本：${VERSION}"

# ---------- 清理旧产物 ----------
rm -rf "${DIST_DIR}/${PACKAGE_NAME}"
mkdir -p "${DIST_DIR}/${PACKAGE_NAME}"

# ---------- 复制项目文件 ----------
echo "==> 复制项目文件..."

# Python 源码
cp -r maplebot           "${DIST_DIR}/${PACKAGE_NAME}/"
cp    bot.py             "${DIST_DIR}/${PACKAGE_NAME}/"
cp    requirements.txt   "${DIST_DIR}/${PACKAGE_NAME}/"
cp    .env               "${DIST_DIR}/${PACKAGE_NAME}/.env"

# ---------- 生成启动脚本 ----------
echo "==> 生成 start.sh..."
cat > "${DIST_DIR}/${PACKAGE_NAME}/start.sh" <<'EOF'
#!/usr/bin/env bash
# 启动脚本（在目标机器上执行）
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 使用 .env.prod（复制为 NoneBot2 默认读取的 .env）
if [ ! -f .env.prod ] && [ -f .env ]; then
  cp .env .env.prod
  echo "[info] 已将 .env 复制为 .env.prod，请按需修改后重新运行。"
fi

# 设置生产环境标志并启动
ENVIRONMENT=prod python3 bot.py
EOF
chmod +x "${DIST_DIR}/${PACKAGE_NAME}/start.sh"

# ---------- 压缩 ----------
echo "==> 压缩为 ${OUTPUT} ..."
tar -czf "${OUTPUT}" \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.pyo' \
  -C "${DIST_DIR}" "${PACKAGE_NAME}"

# ---------- 清理临时目录 ----------
rm -rf "${DIST_DIR}/${PACKAGE_NAME}"

echo "==> 打包完成：${OUTPUT}"
