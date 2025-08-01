# api/views.py
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from src.products import Product, CustomerPricing
from src.assets import Asset
from src.feeds.models import DataFeed, FeedGeneration
from src.core.models import Notification
from src.accounts.models import User


# Placeholder ViewSets - implement serializers and full logic as needed
class ProductViewSet(viewsets.ModelViewSet):
    """API ViewSet for products"""
    queryset = Product.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_customer:
            # Filter products available to customer
            queryset = queryset.filter(
                customer_prices__customer=self.request.user
            ).distinct()
        return queryset


class AssetViewSet(viewsets.ModelViewSet):
    """API ViewSet for assets"""
    queryset = Asset.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_customer:
            # Filter by allowed categories
            if self.request.user.allowed_asset_categories:
                queryset = queryset.filter(
                    categories__slug__in=self.request.user.allowed_asset_categories
                ).distinct()
        return queryset


class FeedViewSet(viewsets.ModelViewSet):
    """API ViewSet for feeds"""
    queryset = DataFeed.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_customer:
            queryset = queryset.filter(customer=self.request.user)
        return queryset


# Authentication endpoints
@api_view(['POST'])
def api_login(request):
    """API login endpoint"""
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({
            'error': 'Username and password required'
        }, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=username, password=password)
    if user:
        login(request, user)
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
            }
        })

    return Response({
        'error': 'Invalid credentials'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def api_logout(request):
    """API logout endpoint"""
    logout(request)
    return Response({'success': True})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def refresh_token(request):
    """Refresh authentication token"""
    # Implement token refresh logic if using token auth
    return Response({'message': 'Token refresh not implemented'})


# Product endpoints
class ProductSearchView(APIView):
    """Search products API"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.GET.get('q', '')
        products = Product.objects.filter(
            name__icontains=query
        )[:20]

        return Response({
            'results': [
                {
                    'id': p.id,
                    'sku': p.sku,
                    'name': p.name,
                    'brand': p.brand.name,
                }
                for p in products
            ]
        })


class ProductFitmentAPIView(APIView):
    """Get product fitment data"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        fitments = product.fitments.select_related('make', 'model')

        return Response({
            'product': product.sku,
            'fitments': [
                {
                    'id': f.id,
                    'make': f.make.name,
                    'model': f.model.name,
                    'years': f"{f.year_start}-{f.year_end}",
                    'submodel': f.submodel,
                    'engine': f.engine,
                }
                for f in fitments
            ]
        })


class CustomerPricingAPIView(APIView):
    """Get customer-specific pricing"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)

        # Get customer pricing if exists
        customer_price = None
        if request.user.is_customer:
            try:
                cp = CustomerPricing.objects.get(
                    customer=request.user,
                    product=product
                )
                customer_price = {
                    'price': str(cp.price),
                    'discount_percent': str(cp.discount_percent) if cp.discount_percent else None,
                }
            except CustomerPricing.DoesNotExist:
                pass

        return Response({
            'product': product.sku,
            'msrp': str(product.msrp) if product.msrp else None,
            'customer_price': customer_price,
        })


class BulkProductUpdateView(APIView):
    """Bulk update products"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_employee:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        # Implement bulk update logic
        return Response({
            'message': 'Bulk update not implemented'
        })


# Asset endpoints
class AssetUploadAPIView(APIView):
    """Upload assets via API"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_employee:
            return Response({
                'error': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        # Implement file upload logic
        return Response({
            'message': 'Asset upload not implemented'
        })


class AssetDownloadAPIView(APIView):
    """Download asset via API"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        asset = get_object_or_404(Asset, pk=pk)

        # Check permissions
        if request.user.is_customer:
            # Check category access
            categories = asset.categories.all()
            can_access = any(
                request.user.can_access_asset_category(cat.slug)
                for cat in categories
            )
            if not can_access:
                return Response({
                    'error': 'Access denied'
                }, status=status.HTTP_403_FORBIDDEN)

        # Return download URL
        return Response({
            'download_url': f"/assets/download/{asset.id}/",
            'filename': asset.original_filename,
            'size': asset.file_size,
        })


class AssetSearchView(APIView):
    """Search assets API"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.GET.get('q', '')
        assets = Asset.objects.filter(
            title__icontains=query,
            is_active=True
        )[:20]

        return Response({
            'results': [
                {
                    'id': a.id,
                    'title': a.title,
                    'type': a.asset_type,
                    'size': a.file_size,
                }
                for a in assets
            ]
        })


# Feed endpoints
class GenerateFeedAPIView(APIView):
    """Generate feed via API"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        feed = get_object_or_404(DataFeed, pk=pk)

        # Check permissions
        if request.user.is_customer and feed.customer != request.user:
            return Response({
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)

        # Queue feed generation
        from src.core.models import TaskQueue
        task = TaskQueue.objects.create(
            task_type='feed_generation',
            task_data={'feed_id': feed.id},
            created_by=request.user
        )

        return Response({
            'task_id': str(task.task_id),
            'status': 'queued'
        })


class FeedStatusAPIView(APIView):
    """Get feed generation status"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        feed = get_object_or_404(DataFeed, pk=pk)

        # Check permissions
        if request.user.is_customer and feed.customer != request.user:
            return Response({
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)

        # Get latest generation
        latest = feed.generations.order_by('-started_at').first()

        if not latest:
            return Response({
                'status': 'no_generations'
            })

        return Response({
            'generation_id': str(latest.generation_id),
            'status': latest.status,
            'started_at': latest.started_at,
            'completed_at': latest.completed_at,
            'row_count': latest.row_count,
        })


class FeedDownloadAPIView(APIView):
    """Download feed via API"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, generation_id):
        generation = get_object_or_404(FeedGeneration, generation_id=generation_id)

        # Check permissions
        if request.user.is_customer and generation.feed.customer != request.user:
            return Response({
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'download_url': f"/feeds/download/{generation_id}/",
            'filename': generation.file_path.split('/')[-1] if generation.file_path else None,
            'size': generation.file_size,
        })


# Notification endpoints
class NotificationListAPIView(generics.ListAPIView):
    """List user notifications"""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read_api(request, pk):
    """Mark notification as read"""
    notification = get_object_or_404(
        Notification,
        pk=pk,
        user=request.user
    )
    notification.mark_as_read()
    return Response({'success': True})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read_api(request):
    """Mark all notifications as read"""
    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    return Response({'success': True})


# User endpoints
class UserProfileAPIView(APIView):
    """Get/update user profile"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'company_name': user.company_name,
        })

    def patch(self, request):
        # Implement profile update
        return Response({
            'message': 'Profile update not implemented'
        })


class UserSettingsAPIView(APIView):
    """Get/update user settings"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'notification_preferences': request.user.notification_preferences,
        })

    def patch(self, request):
        # Implement settings update
        return Response({
            'message': 'Settings update not implemented'
        })


# System endpoints
@api_view(['GET'])
def health_check_api(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
    })


class SystemStatsAPIView(APIView):
    """System statistics (admin only)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not request.user.is_admin:
            return Response({
                'error': 'Admin access required'
            }, status=status.HTTP_403_FORBIDDEN)

        return Response({
            'products': Product.objects.count(),
            'assets': Asset.objects.count(),
            'users': User.objects.count(),
            'feeds': DataFeed.objects.count(),
        })


# Webhook endpoints
class ProductUpdateWebhook(APIView):
    """Webhook for external product updates"""
    permission_classes = []  # Configure based on your security needs

    def post(self, request):
        # Implement webhook logic
        return Response({
            'message': 'Webhook received'
        })


class InventoryUpdateWebhook(APIView):
    """Webhook for inventory updates"""
    permission_classes = []  # Configure based on your security needs

    def post(self, request):
        # Implement webhook logic
        return Response({
            'message': 'Webhook received'
        })