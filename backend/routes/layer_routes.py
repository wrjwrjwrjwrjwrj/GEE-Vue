from flask import Blueprint, jsonify, request
from services.layer_service import get_layer_info_service, update_vis_params_service
from services.map_service import get_dataset  # 导入函数而不是变量

layer_bp = Blueprint('layer', __name__)

@layer_bp.route('/layer-info', methods=['GET'])
def get_layer_info():
    try:
        layer_id = request.args.get('id', '0')

        satellite = request.args.get('satellite', 'LANDSAT')
        current_dataset = get_dataset(layer_id)
        result = get_layer_info_service(current_dataset, satellite)
        print(f"Layer_routes.py - get_layer_info - result: {result}")
        return jsonify(result)
    except Exception as e:
        print(f"Layer_routes.py - Error in get_layer_info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@layer_bp.route('/update-vis-params', methods=['POST'])
def update_vis_params():
    try:
        data = request.json
        print(f"Layer_routes.py - Received data: {data}")
        layer_id = data.get('layerId')  # 从请求中获取图层ID
        print(f"Layer_routes.py - update_vis_params-layer_id: {layer_id}")
        
        # 获取对应图层的 dataset
        current_dataset = get_dataset(layer_id)
        if not current_dataset:
            raise Exception(f"Layer_routes.py - No dataset found for layer {layer_id}")
        
        # 传入当前的 dataset
        result = update_vis_params_service(data, current_dataset)
        return jsonify(result)
    except Exception as e:
        print(f"Layer_routes.py - Error in update_vis_params: {str(e)}")
        return jsonify({'error': str(e)}), 500 