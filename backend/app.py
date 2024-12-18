from flask import Flask
from flask_cors import CORS
import ee

from routes.map_routes import map_bp
from routes.layer_routes import layer_bp
from routes.tool_routes import tool_bp
from setting import init_earth_engine

app = Flask(__name__)
CORS(app)

# 初始化 Earth Engine
init_earth_engine()

# 注册路由蓝图
app.register_blueprint(map_bp)
app.register_blueprint(layer_bp)
app.register_blueprint(tool_bp, url_prefix='/tools')

if __name__ == '__main__':
    app.run(debug=True)
