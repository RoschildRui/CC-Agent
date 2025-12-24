#!/bin/bash

################################################################################
# Polyscore 一键安装脚本 (Linux)
# 版本: 1.0
# 日期: 2025-12-13
# 说明: 在没有 Python 的环境中自动安装 uv、创建虚拟环境并启动应用
################################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印欢迎信息
print_welcome() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}   Polyscore - AI 驱动的产品市场分析系统${NC}"
    echo "   一键安装脚本 (Linux)"
    echo "   版本: v1.0 (2025-12-13)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# 检测操作系统
detect_os() {
    print_info "检测操作系统..."

    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        print_success "检测到 Linux 系统"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        print_success "检测到 macOS 系统"
    else
        print_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
}

# 检查 uv 是否已安装
check_uv() {
    print_info "检查 uv 是否已安装..."

    if command -v uv &> /dev/null; then
        UV_VERSION=$(uv --version 2>&1 | head -n 1)
        print_success "uv 已安装: $UV_VERSION"
        return 0
    else
        print_warning "uv 未安装"
        return 1
    fi
}

# 安装 uv
install_uv() {
    print_info "开始安装 uv..."

    if curl -LsSf https://astral.sh/uv/install.sh | sh; then
        print_success "uv 安装成功"

        # 添加 uv 到 PATH（临时）
        export PATH="$HOME/.local/bin:$PATH"

        # 提示用户永久添加到 PATH
        print_warning "请将以下命令添加到你的 shell 配置文件 (~/.bashrc 或 ~/.zshrc):"
        echo '  export PATH="$HOME/.local/bin:$PATH"'
        echo ""

        # 验证安装
        if command -v uv &> /dev/null; then
            UV_VERSION=$(uv --version 2>&1 | head -n 1)
            print_success "uv 验证成功: $UV_VERSION"
        else
            print_error "uv 安装后无法找到，请检查 PATH 配置"
            exit 1
        fi
    else
        print_error "uv 安装失败"
        exit 1
    fi
}

# 检查 Python
check_python() {
    print_info "检查 Python..."

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_success "发现 Python: $PYTHON_VERSION"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version)
        print_success "发现 Python: $PYTHON_VERSION"
        PYTHON_CMD="python"
    else
        print_warning "未发现 Python，uv 将自动管理 Python 环境"
        PYTHON_CMD=""
    fi
}

# 创建虚拟环境
create_venv() {
    print_info "创建虚拟环境..."

    if [ -d ".venv" ]; then
        print_warning "虚拟环境已存在，跳过创建"
    else
        if uv venv; then
            print_success "虚拟环境创建成功"
        else
            print_error "虚拟环境创建失败"
            exit 1
        fi
    fi
}

# 激活虚拟环境
activate_venv() {
    print_info "激活虚拟环境..."

    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        print_success "虚拟环境已激活"
    else
        print_error "找不到虚拟环境激活脚本"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    print_info "安装 Python 依赖..."

    if [ ! -f "requirements.txt" ]; then
        print_error "找不到 requirements.txt 文件"
        exit 1
    fi

    print_info "使用 uv 安装依赖（这可能需要几分钟）..."

    if uv pip install -r requirements.txt; then
        print_success "依赖安装成功"
    else
        print_error "依赖安装失败"
        exit 1
    fi
}

# 检查必要的目录和文件
check_structure() {
    print_info "检查项目结构..."

    # 必需的目录
    REQUIRED_DIRS=("agent" "models" "static" "templates" "data" "reports")

    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            print_warning "创建缺失的目录: $dir"
            mkdir -p "$dir"
        fi
    done

    # 必需的子目录
    mkdir -p data/conversations
    mkdir -p data/accountsData
    mkdir -p data/inviteData

    # 检查必需的文件
    if [ ! -f "app.py" ]; then
        print_error "找不到 app.py 文件，请确认在正确的目录中运行此脚本"
        exit 1
    fi

    # 创建 tasks.json 如果不存在
    if [ ! -f "data/tasks.json" ]; then
        echo "[]" > data/tasks.json
        print_success "已创建 data/tasks.json"
    fi

    print_success "项目结构检查完成"
}

# 检查 AI 模型配置
check_config() {
    print_info "检查配置文件..."

    # 检查 .env 文件是否存在
    if [ ! -f ".env" ]; then
        print_warning ".env 配置文件不存在"
        if [ -f "env_example.txt" ]; then
            print_info "从模板创建 .env 文件..."
            cp env_example.txt .env
            print_success "已创建 .env 文件，请编辑此文件填入实际的 API 密钥"
        else
            print_error "未找到 env_example.txt 模板文件"
        fi
    else
        print_success ".env 配置文件已存在"
    fi

    # 检查是否有至少一个模型配置
    if ls models/*/*.json &> /dev/null; then
        print_success "发现 AI 模型配置文件"

        # 警告：需要配置 API 密钥
        print_warning "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        print_warning "重要提示: 请确保已在 .env 文件中配置 API 密钥"
        print_warning "参考: env_example.txt"
        print_warning "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
    else
        print_error "未找到 AI 模型配置文件"
        print_error "请在 models/ 目录下添加至少一个提供商的配置"
        exit 1
    fi
}

# 启动应用
start_app() {
    print_info "准备启动应用..."

    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "   安装完成！正在启动 Polyscore..."
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    print_info "应用将在以下地址运行："
    echo -e "${GREEN}   http://localhost:5001${NC}"
    echo ""
    print_info "按 Ctrl+C 停止应用"
    echo ""
    sleep 2

    # 启动应用
    python app.py
}

# 错误处理函数
cleanup_on_error() {
    print_error "安装过程中发生错误"
    print_info "请检查上述错误信息并重试"
    exit 1
}

# 设置错误陷阱
trap cleanup_on_error ERR

################################################################################
# 主流程
################################################################################

main() {
    print_welcome

    # 步骤 1: 检测操作系统
    detect_os

    # 步骤 2: 检查并安装 uv
    if ! check_uv; then
        install_uv
    fi

    # 步骤 3: 检查 Python
    check_python

    # 步骤 4: 检查项目结构
    check_structure

    # 步骤 5: 创建虚拟环境
    create_venv

    # 步骤 6: 激活虚拟环境
    activate_venv

    # 步骤 7: 安装依赖
    install_dependencies

    # 步骤 8: 检查配置
    check_config

    # 步骤 9: 启动应用
    start_app
}

################################################################################
# 命令行选项处理
################################################################################

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help          显示此帮助信息"
    echo "  -n, --no-start      只安装依赖，不启动应用"
    echo "  -c, --check-only    只检查环境，不执行安装"
    echo ""
    echo "示例:"
    echo "  $0                  # 完整安装并启动"
    echo "  $0 --no-start       # 只安装，不启动"
    echo "  $0 --check-only     # 只检查环境"
    echo ""
}

# 解析命令行参数
NO_START=false
CHECK_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--no-start)
            NO_START=true
            shift
            ;;
        -c|--check-only)
            CHECK_ONLY=true
            shift
            ;;
        *)
            print_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

################################################################################
# 执行主流程
################################################################################

if [ "$CHECK_ONLY" = true ]; then
    print_welcome
    detect_os
    check_uv
    check_python
    check_structure
    check_config
    print_success "环境检查完成"
elif [ "$NO_START" = true ]; then
    print_welcome
    detect_os
    if ! check_uv; then
        install_uv
    fi
    check_python
    check_structure
    create_venv
    activate_venv
    install_dependencies
    check_config
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    print_success "   安装完成！"
    print_success "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    print_info "手动启动应用:"
    echo "  source .venv/bin/activate"
    echo "  python app.py"
    echo ""
else
    main
fi
