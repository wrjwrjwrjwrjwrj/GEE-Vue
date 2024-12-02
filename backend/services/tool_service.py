import ee

class ToolService:
    @staticmethod
    def RemoveBit(image):
        """除云除雪函数"""
        snow_bit = 1 << 5
        dilated_cloud = 1 << 1  # 扩张云
        cloud_shadow_bit_mask = 1 << 4
        clouds_bit_mask = 1 << 3
        
        qa = image.select("QA_PIXEL").toInt()
        mask = (
            qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0)
            .And(qa.bitwiseAnd(clouds_bit_mask).eq(0))
            .And(qa.bitwiseAnd(snow_bit).eq(0))
            .And(qa.bitwiseAnd(dilated_cloud).eq(0))
        )
        return image.updateMask(mask)

    @staticmethod
    def cloud_removal(image):
        """影像除云处理"""
        try:
            cleared_image = ToolService.RemoveBit(image)
            
            return cleared_image 
            
        except Exception as e:
            raise Exception(f"Tool_service.py - Error in cloud removal: {str(e)}")

    @staticmethod
    def calculate_index(image, index_type, params=None):
        """计算指数（NDVI, NDWI等）"""
        try:
            if index_type == 'ndvi':
                # 计算NDVI
                nir = image.select('B5')  # Landsat 8 NIR band
                red = image.select('B4')  # Landsat 8 Red band
                ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
                return ndvi
            elif index_type == 'ndwi':
                # 计算NDWI
                nir = image.select('B5')
                green = image.select('B3')
                ndwi = green.subtract(nir).divide(green.add(nir)).rename('NDWI')
                return ndwi
            # 可以添加更多指数计算
            return {
                'success': True,
                'message': f'{index_type} 计算完成'
            }
        except Exception as e:
            raise Exception(f"Tool_service.py - Error calculating {index_type}: {str(e)}")

    @staticmethod
    def supervised_classification(image, training_data, params):
        """监督分类"""
        try:
            # 实现监督分类逻辑
            return {
                'success': True,
                'message': '监督分类完成'
            }
        except Exception as e:
            raise Exception(f"Tool_service.py - Error in supervised classification: {str(e)}")

    @staticmethod
    def image_filling(images):
        try:
            # 将图像列表转换为 ImageCollection
            imageCollection = ee.ImageCollection.fromImages(images)
            
            def fillGaps(image):
                # 过滤掉当前图像
                sourceCollection = imageCollection.filter(
                    ee.Filter.neq('system:index', image.get('system:index')))
                # 使用其他图像的镶嵌来填补当前图像的缺失部分
                filled = image.unmask(sourceCollection.mosaic())
                return filled
            
            # 对每个图像进行填补处理

            filled_images = imageCollection.map(fillGaps)

            # filled_images = []
            # for img in images:
            #     filled = fillGaps(ee.Image(img), imageCollection)
            #     filled_images.append(filled)
                
            return filled_images
            
        except Exception as e:
            raise Exception(f"Tool_service.py - Error in image_filling: {str(e)}")