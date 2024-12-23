from flask import Blueprint, jsonify, request
from services.map_service import save_dataset
from tools.preprocessing import PreprocessingTool
from tools.classification import ClassificationTool 
from tools.calculateIndex import IndexTool
import ee

tool_bp = Blueprint('tool', __name__)

datasets = None

def common_process(layer_ids, results, vis_params, message):
    '''
    通用的图层处理函数
    '''
    layer_results = []
    for i, layer_id in enumerate(layer_ids):
        result = ee.Image(results.get(i))
        datasets[layer_id] = result
        
        layer_vis = next((v for v in vis_params if v['id'] == layer_ids[i]), None)
        params = layer_vis['visParams'] if layer_vis else {
            'bands': ['B4', 'B3', 'B2'],
            'min': 0,
            'max': 0.3,
            'gamma': 1.4
        }
        
        map_id = result.getMapId(params)
        
        layer_results.append({
            'layer_id': layer_ids[i],
            'tileUrl': map_id['tile_fetcher'].url_format
        })

    return jsonify({
        'success': True,
        'message': message,
        'results': layer_results
    })

@tool_bp.route('/cloud-removal', methods=['POST'])
def cloud_removal():
    try:
        data = request.json
        layer_ids = data.get('layer_ids')
        vis_params = data.get('vis_params', [])
        
        PreprocessingTool.validate_inputs(layer_ids, datasets)
        selected_images = PreprocessingTool.get_image_collection(layer_ids, datasets)
        results = selected_images.map(PreprocessingTool.cloud_removal).toList(selected_images.size())
        
        return common_process(layer_ids, results, vis_params, '除云处理完成')
        
    except Exception as e:
        print(f"Error in cloud_removal: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@tool_bp.route('/calculate-index', methods=['POST'])
def calculate_index():
    try:
        data = request.json
        layer_ids = data.get('layer_ids')
        index_type = data.get('index_type')
        vis_params = data.get('vis_params', [])
        
        IndexTool.validate_inputs(layer_ids, datasets)
        selected_images = IndexTool.get_image_collection(layer_ids, datasets).toList(len(layer_ids))
        
        # 修改这里，传入layer_id
        results = []
        for i, layer_id in enumerate(layer_ids):
            image = ee.Image(selected_images.get(i))
            result = IndexTool.calculate_index(image, index_type, layer_id)
            results.append(result)
            
        results = ee.List(results)
        return common_process(layer_ids, results, vis_params, f'已添加 {index_type.upper()} 波段')
        
    except Exception as e:
        print(f"Error in calculate_index: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@tool_bp.route('/supervised-classification', methods=['POST'])
def supervised_classification():
    try:
        data = request.json
        result = ClassificationTool.supervised_classification(
            data.get('image'),
            data.get('training_data'),
            data.get('params')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@tool_bp.route('/image-filling', methods=['POST'])
def image_filling():
    try:
        data = request.json
        layer_ids = data.get('layer_ids')
        vis_params = data.get('vis_params', [])
        
        PreprocessingTool.validate_inputs(layer_ids, datasets)
        
        # 获取图像集合
        selected_images = PreprocessingTool.get_image_collection(layer_ids, datasets)
        # 转换为列表以便处理
        images_list = selected_images.toList(selected_images.size())
        
        # 创建图像集合用于填补
        image_collection = ee.ImageCollection.fromImages(images_list)
        
        # 对每个图像进行填补处理，并添加状态标记
        results = images_list.map(
            lambda img: PreprocessingTool.image_filling(ee.Image(img), image_collection)
        )
        
        #防止填补失败时出错
        print('Tool_routes.py - image_filling-results:',results.size().getInfo())
        # 使用 common_process 处理结果
        return common_process(layer_ids, results, vis_params, '图像填补处理完成')
        
    except Exception as e:
        print(f"Error in image_filling: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@tool_bp.route('/get-layers', methods=['GET'])
def get_layers():
    try:
        global datasets
        from services.map_service import get_all_datasets
        datasets, datasetsNames = get_all_datasets()
        landsat_layers = {}
        
        for layer_id, dataset in datasets.items():
            if 'LANDSAT' in layer_id.upper():
                layer_name = datasetsNames[layer_id]
                landsat_layers[layer_id] = {
                    'id': layer_id,
                    'name': layer_name,
                    'dataset': dataset
                }
        
        return jsonify({
            'success': True,
            'layers': [
                {
                    'id': layer_id,
                    'name': info['name']
                } for layer_id, info in landsat_layers.items()
            ]
        })
    except Exception as e:
        print(f"Error in get_layers: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to get Landsat layers'
        }), 500 

@tool_bp.route('/kmeans-clustering', methods=['POST'])
def kmeans_clustering():
    try:
        data = request.json
        layer_ids = data.get('layer_ids')
        cluster_counts = data.get('cluster_counts', {})
        
        ClassificationTool.validate_inputs(layer_ids, datasets)
        selected_images = ClassificationTool.get_image_collection(layer_ids, datasets)
        
        # 为每个图像执行聚类
        results = []
        num = len(layer_ids)
        for i, layer_id in enumerate(layer_ids):
            num_clusters = cluster_counts.get(layer_id, 5)
            print('Tool_routes.py - kmeans_clustering-num_clusters',num_clusters)
            result = ClassificationTool.kmeans_clustering(
                ee.Image(selected_images.toList(num).get(i)), 
                num_clusters
            )
            results.append(result)
        
        # 处理结果
        layer_results = []
        bandInfo = ['cluster']
        for i, layer_id in enumerate(layer_ids):
            num_clusters = cluster_counts.get(layer_id, 5)
            kmeans_id = f"{layer_id}_kmeans"
            
            save_dataset(kmeans_id, results[i].select(bandInfo), 'kmeans')
            
            map_id = datasets[kmeans_id].getMapId({
                'min': 0,
                'max': num_clusters - 1
            })
            
            layer_results.append({
                'layer_id': kmeans_id,
                'tileUrl': map_id['tile_fetcher'].url_format,
                'bandInfo': bandInfo,
                'visParams': {
                    'bands': bandInfo,
                    'min': 0,
                    'max': num_clusters - 1
                }
            })

        return jsonify({
            'success': True,
            'message': 'K-means聚类分析完成',
            'results': layer_results
        })
        
    except Exception as e:
        print(f"Error in kmeans_clustering: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500 

@tool_bp.route('/histogram-equalization', methods=['POST'])
def histogram_equalization():
    try:
        data = request.json
        layer_ids = data.get('layer_ids')
        vis_params = data.get('vis_params', [])
        
        PreprocessingTool.validate_inputs(layer_ids, datasets)
        selected_images = PreprocessingTool.get_image_collection(layer_ids, datasets)
        results = selected_images.map(PreprocessingTool.histogram_equalization).toList(selected_images.size())
        
        return common_process(layer_ids, results, vis_params, '直方图均衡化处理完成')
        
    except Exception as e:
        print(f"Error in histogram_equalization: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@tool_bp.route('/get-assets', methods=['GET'])
def get_assets():
    try:
        # 从 GEE 认证中获取用户信息
        credentials = ee.data.getAssetRoots()
        if not credentials:
            raise Exception("未找到 GEE 认证信息")
        print('Tool_routes.py - get_assets-credentials:', credentials)
            
        # 获取所有根文件夹的资产
        formatted_assets = []
        for cred in credentials:
            root_folder = cred['id']
            print('Tool_routes.py - get_assets-root_folder:', root_folder)
            
            try:
                # 列出该根文件夹下的所有资产
                assets = ee.data.listAssets({'parent': root_folder})
                
                # 格式化该文件夹下的资产
                folder_assets = []
                for asset in assets['assets']:
                    asset_info = {
                        'id': asset['id'],
                        'name': asset['id'].split('/')[-1],
                        'type': asset['type'],
                        'path': asset['id'],
                        'title': asset.get('title', ''),
                        'description': asset.get('description', ''),
                        'tags': asset.get('tags', [])
                    }
                    
                    # 如果是文件夹，递归获取子资产
                    if asset['type'] == 'FOLDER':
                        try:
                            sub_assets = ee.data.listAssets({'parent': asset['id']})
                            asset_info['children'] = [{
                                'id': sub['id'],
                                'name': sub['id'].split('/')[-1],
                                'type': sub['type'],
                                'path': sub['id'],
                                'title': sub.get('title', ''),
                                'description': sub.get('description', '')
                            } for sub in sub_assets['assets']]
                        except Exception as sub_error:
                            print(f"Error listing sub-assets for {asset['id']}: {str(sub_error)}")
                            asset_info['children'] = []
                    
                    folder_assets.append(asset_info)
                
                # 创建根文件夹节点
                root_info = {
                    'id': root_folder,
                    'name': root_folder.split('/')[-1],
                    'type': 'FOLDER',
                    'path': root_folder,
                    'children': folder_assets
                }
                
                formatted_assets.append(root_info)
                
            except Exception as folder_error:
                print(f"Error accessing folder {root_folder}: {str(folder_error)}")
                continue
            
        return jsonify({
            'success': True,
            'assets': formatted_assets
        })
        
    except Exception as e:
        print(f"Error in get_assets: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@tool_bp.route('/add-vector-asset', methods=['POST'])
def add_vector_asset():
    try:
        data = request.json
        asset_id = data.get('asset_id')
        
        # 获取矢量数据
        
        vector_asset = ee.FeatureCollection(asset_id)    # print(ve
        
        # 将 FeatureCollection 转换为 GeoJSON
        features = vector_asset.getInfo()
        print('Tool_routes.py - add_vector_asset-features:',vector_asset.size().getInfo())
        
        return jsonify({
            'success': True,
            'features': features
        })
        
    except Exception as e:
        print(f"Error in add_vector_asset: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@tool_bp.route('/add-image-asset', methods=['POST'])
def add_image_asset():
    try:
        data = request.json
        asset_id = data.get('asset_id')
        
        # 获取影像数据
        image_asset = ee.Image(asset_id)
        
        # 获取可视化参数
        vis_params = {
            'bands': ['B4', 'B3', 'B2'],
            'min': 0,
            'max': 3000,
            'gamma': 1.4
        }
        
        # 获取瓦片URL
        map_id = image_asset.getMapId(vis_params)
        
        return jsonify({
            'success': True,
            'tileUrl': map_id['tile_fetcher'].url_format
        })
        
    except Exception as e:
        print(f"Error in add_image_asset: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500