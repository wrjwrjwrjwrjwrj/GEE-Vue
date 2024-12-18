from flask import Blueprint, jsonify, request
from services.map_service import get_map_data_service,remove_dataset,compute_image_stats,get_dataset
import ee

map_bp = Blueprint('map', __name__)

# 存储研究区域列表
study_areas = []

@map_bp.route('/map-data', methods=['GET'])
def get_map_data():
    try:
        # 获取前端参数
        satellite = request.args.get('satellite', 'LANDSAT')
        start_date = request.args.get('startDate', '2023-01-01')
        end_date = request.args.get('endDate', '2023-12-31')
        cloud_cover = float(request.args.get('cloudCover', 20))
        layerName = request.args.get('layerName',None)
        
        print(f"Map_routes.py - Received satellite: {satellite}, startDate: {start_date}," +
              f"endDate: {end_date}, cloudCover: {cloud_cover}, layerName:{layerName}")
        
        # 如果有多个研究区域，将它们合并成一个多边形
        merged_area = None
        if study_areas:
            # 将所有多边形合并成一个
            merged_area = ee.Geometry.MultiPolygon(study_areas)

        # 传入合并后的研究区域进行筛选和裁���
        result = get_map_data_service(satellite, start_date, end_date, 
                                      cloud_cover, merged_area,layerName)
        return jsonify(result)
        
    except Exception as e:
        print(f"Map_routes.py - Error in get_map_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500 
    
@map_bp.route('/filter-by-geometry', methods=['POST'])
def filter_by_geometry():
    try:
        global study_areas
        data = request.json
        
        if data.get('type') == 'vector':
            # 处理矢量资产
            asset_id = data.get('asset_id')
            vector_asset = ee.FeatureCollection(asset_id)
            
            # 获取矢量的几何信息
            geometry = vector_asset.geometry().getInfo()
            
            # 将几何信息添加到研究区域列表
            study_areas.append(geometry['coordinates'][0])
            
            print(f"Map_routes.py - Added vector asset as study area. Total areas: {len(study_areas)}")
            
        else:
            # 处理手动绘制的几何图形（原有逻辑）
            geometry = data['geometry']
            study_areas.append(geometry['coordinates'][0])
            
        return jsonify({
            'success': True,
            'message': f'Study area added successfully. Total areas: {len(study_areas)}'
        })

    except Exception as e:
        print(f"Map_routes.py - Error in filter_by_geometry: {str(e)}")
        return jsonify({'error': str(e)}), 500

@map_bp.route('/remove-geometry', methods=['POST'])
def remove_geometry():
    try:
        global study_areas
        data = request.json
        deleted_coordinates = data['coordinates']
        
        # 将要删除的坐标转换为字符串进行比较
        deleted_str = [str(coords) for coords in deleted_coordinates]
        
        # 过滤掉被删除的坐标
        study_areas = [area for area in study_areas 
                      if str(area) not in deleted_str]
        
        
        print(f"Map_routes.py - Removed geometries. Remaining areas: {len(study_areas)}")
        
        return jsonify({
            'success': True,
            'message': f'Geometries removed successfully. Remaining areas: {len(study_areas)}'
        })

    except Exception as e:
        print(f"Map_routes.py - Error in remove_geometry: {str(e)}")
        return jsonify({'error': str(e)}), 500

@map_bp.route('/remove-layer', methods=['POST'])
def remove_layer():
    try:
        data = request.get_json()
        layer_id = data.get('layer_id')
        
        
        if not layer_id:
            return jsonify({
                'success': False,
                'message': '缺少图层ID'
            }), 400
            
        # 调用已有的 remove_dataset 服务
        remove_dataset(layer_id)
        
        return jsonify({
            'success': True,
            'message': '图层已从数据集中移除'
        })
        
    except Exception as e:
        print(f"Map_routes.py - Error removing layer: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'移除图层时发生错误: {str(e)}'
        }), 500

@map_bp.route('/compute-stats', methods=['POST'])
def compute_band_stats():
    try:
        data = request.get_json()
        layer_id = data.get('layer_id')
        bands = data.get('bands')
        
        if not layer_id or not bands:
            return jsonify({
                'success': False,
                'message': '缺少必要参数'
            }), 400
            
        # 从服务中获取数据集
        dataset = get_dataset(layer_id)
        if not dataset:
            return jsonify({
                'success': False,
                'message': '未找到指定图层'
            }), 404
            
        # 获取当前的研究区域
        merged_area = None
        if study_areas:
            merged_area = ee.Geometry.MultiPolygon(study_areas)
            
        # 计算统计值
        stats = compute_image_stats(dataset, bands, merged_area)
        
        if stats:
            stats_dict = stats.getInfo()
            print(f"Map_routes.py - Final stats: min={stats_dict.get('global_min')}, max={stats_dict.get('global_max')}")
            return jsonify({
                'success': True,
                'min': stats_dict.get('global_min'),
                'max': stats_dict.get('global_max')
            })
        else:
            return jsonify({
                'success': False,
                'message': '计算统计值失败'
            }), 500
            
    except Exception as e:
        print(f"Map_routes.py - Error computing stats: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'计算统计值时发生错误: {str(e)}'
        }), 500