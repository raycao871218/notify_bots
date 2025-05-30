#!/bin/bash

# 获取脚本所在目录的上一层目录
PARENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && cd .. && pwd)"

# 加载环境变量
if [ -f "$PARENT_DIR/.env" ]; then
    export $(cat "$PARENT_DIR/.env" | grep -v '^#' | xargs)
else
    echo "❌ 错误：未找到 .env 文件，请确保文件位于 $PARENT_DIR/.env"
    exit 1
fi

# 检查必要的环境变量
if [ -z "$SERVER_IP" ] || [ -z "$SSH_USER" ]; then
    echo "❌ 错误：必需的环境变量未设置"
    echo "请确保在 .env 文件中设置了以下变量："
    echo "- SERVER_IP（服务器主机名或IP地址）"
    echo "- SSH_USER（SSH用户名）"
    exit 1
fi

# 检查其他必要的环境变量
if [ -z "$NAS_CERT_DIR" ] || [ -z "$NAS_CERT_SITE_NAME" ] || [ -z "$SERVER_CERT_DIR" ] || [ -z "$DOMAIN_NAME" ]; then
    echo "❌ 错误：必需的环境变量未设置"
    echo "请确保在 .env 文件中设置了以下变量："
    echo "- NAS_CERT_DIR（NAS上证书存放的目录）"
    echo "- NAS_CERT_SITE_NAME（证书站点名称）"
    echo "- SERVER_CERT_DIR（服务器上证书存放的目录）"
    echo "- DOMAIN_NAME （域名）"
    exit 1
fi

# 截取域名前缀
DOMAIN_PREFIX = "${DOMAIN_NAME%%.*}"

# 确保目标目录存在
SERVER_CERT_END_DIR="$SERVER_CERT_DIR/$DOMAIN_PREFIX"
NAS_CERT_END_DIR="$NAS_CERT_DIR/$NAS_CERT_SITE_NAME"

echo "正在同步证书文件..."
echo "正在执行命令：ssh $SSH_USER@$SERVER_IP mkdir -p $SERVER_CERT_END_DIR"
# 创建目标目录
ssh "$SSH_USER@$SERVER_IP" "mkdir -p $SERVER_CERT_END_DIR"

echo "正在执行命令：rsync -avz --delete $NAS_CERT_END_DIR/ $SSH_USER@$SERVER_IP:$SERVER_CERT_END_DIR/"
# 使用rsync同步证书文件
rsync -avz --delete \
    "$NAS_CERT_END_DIR/" \
    "$SSH_USER@$SERVER_IP:$SERVER_CERT_END_DIR/"

# 检查同步是否成功
if [ $? -eq 0 ]; then
    echo "✅ 证书同步成功"
    
    echo "正在重启Nginx服务..."
    # 重启Nginx服务以应用新证书
    ssh "$SSH_USER@$SERVER_IP" "sudo nginx -s reload"
    
    if [ $? -eq 0 ]; then
        echo "✅ Nginx服务已重启"
    else
        echo "❌ Nginx服务重启失败"
        exit 1
    fi
else
    echo "❌ 证书同步失败"
    exit 1
fi