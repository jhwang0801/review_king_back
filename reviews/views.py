import boto3, uuid

from django.http  import JsonResponse
from django.views import View
from django.db    import transaction

from reviews.models       import Review, ReviewImage, ProductPurchasedWith, KeywordFromReview
from products.models      import Product, SubCategory
from core.utils           import login_decorator
from core.review_keyword  import review_keyword
from review_king.settings import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_STORAGE_BUCKET_NAME,
)

class ReviewView(View):
    @login_decorator
    def post(self, request):
        try:
            user       = request.user
            product_id = request.POST['product_id']
            content    = request.POST['content']
            files      = request.FILES.getlist('files')
            product_id_purchased_with = request.POST.getlist('product_id_purchased_with')
            
            s3resource = boto3.resource('s3', aws_access_key_id= AWS_ACCESS_KEY_ID, aws_secret_access_key= AWS_SECRET_ACCESS_KEY)
            
            product = Product.objects.get(id=product_id)
            
            if Review.objects.filter(user_id=user.id, product_id=product_id):
                return JsonResponse({'message' : 'THE_REVIEW_ALREADY_EXISTS'}, status=404)
            
            with transaction.atomic():
                review = Review.objects.create(
                    user    = user,
                    product = product,
                    content = content,
                )
                
                for file in files :
                    file._set_name(str(uuid.uuid4()))
                    s3resource.Bucket(AWS_STORAGE_BUCKET_NAME).put_object(Key='/%s'%(file), Body=file)
                    ReviewImage.objects.create(
                        review  = review,
                        img_url = 'https://review-king-kurly.s3.ap-northeast-2.amazonaws.com/'+"/%s"%(file),
                    )
                    
                for product_id in product_id_purchased_with :
                    ProductPurchasedWith.objects.create(
                        review  = review,
                        product_id = product_id
                    )
                    
                review_keyword_subcategories = review_keyword(review.id)
                for subcategory in review_keyword_subcategories:
                    if SubCategory.objects.get(name=subcategory):
                        subcategory = SubCategory.objects.get(name=subcategory)
                        KeywordFromReview.objects.create(
                            review  = review,
                            sub_category = subcategory
                        )
                        
            return JsonResponse({'Message': 'SUCCESS'}, status=200)
        
        except KeyError:
            return JsonResponse({'Message': 'KEY_ERROR'}, status=400)
        
        except transaction.TransactionManagementError:
            return JsonResponse({'message': 'TransactionManagementError'}, status=400)
        
        except Product.DoesNotExist:
            return JsonResponse({'Message': 'PRODUCT_DOES_NOT_EXIST'}, status=404)