from flask import Flask

app = Flask(__name__)  # 创建一个 Flask 应用

@app.route('/')  # 设置一个 URL 路由，对应网站首页
def home():
    return "Hello, Flask!"

if __name__ == '__main__':
    app.run(debug=True)  # 启动服务，开启调试模式
