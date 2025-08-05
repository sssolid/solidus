# src/api/views.py
import logging

# Serializers (would typically be in separate serializers.py file)
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from assets.models import Asset, AssetDownload
from audit.models import AuditLog
from core.models import Notification
from feeds.models import DataFeed, FeedGeneration
from products.models import CustomerPricing, Product, ProductFitment

logger = logging.getLogger(__name__)


class ProductSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="brand.name", read_only=True)
    categories = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "number",
            "description",
            "brand_name",
            "categories",
            "weight",
            "dimensions",
            "msrp",
            "map_price",
            "is_active",
            "is_featured",
            "created_at",
        ]


class AssetSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Asset
        fields = [
            "id",
            "title",
            "description",
            "asset_type",
            "file_size",
            "file_url",
            "thumbnail_url",
            "is_active",
            "is_public",
            "created_at",
        ]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_thumbnail_url(self, obj):
        return obj.get_thumbnail_url()


class FeedSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.company_name", read_only=True
    )

    class Meta:
        model = DataFeed
        fields = [
            "id",
            "name",
            "description",
            "feed_type",
            "format",
            "customer_name",
            "is_active",
            "created_at",
        ]


# ViewSets
class ProductViewSet(viewsets.ModelViewSet):
    """API ViewSet for products"""

    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Product.objects.select_related("brand").prefetch_related(
            "categories"
        )

        if self.request.user.is_customer:
            # Filter products available to customer
            queryset = queryset.filter(
                customer_prices__customer=self.request.user
            ).distinct()

        # Apply filters
        sku = self.request.query_params.get("sku")
        if sku:
            queryset = queryset.filter(sku__icontains=sku)

        brand = self.request.query_params.get("brand")
        if brand:
            queryset = queryset.filter(brand__name__icontains=brand)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(sku__icontains=search)
                | Q(description__icontains=search)
            )

        return queryset

    @action(detail=True, methods=["get"])
    def fitment(self, request, pk=None):
        """Get product fitment data"""
        product = self.get_object()
        fitments = ProductFitment.objects.filter(product=product)

        fitment_data = []
        for fitment in fitments:
            fitment_data.append(
                {
                    "id": fitment.id,
                    "year_start": fitment.year_start,
                    "year_end": fitment.year_end,
                    "make": fitment.make,
                    "model": fitment.model,
                    "submodel": fitment.submodel,
                    "engine": fitment.engine,
                    "trim": fitment.trim,
                    "notes": fitment.notes,
                }
            )

        return Response(fitment_data)

    @action(detail=True, methods=["get"])
    def pricing(self, request, pk=None):
        """Get customer pricing for product"""
        product = self.get_object()

        if request.user.is_customer:
            try:
                pricing = CustomerPricing.objects.get(
                    customer=request.user, product=product
                )
                return Response(
                    {
                        "price": pricing.price,
                        "discount_percent": pricing.discount_percent,
                        "valid_from": pricing.valid_from,
                        "valid_until": pricing.valid_until,
                        "notes": pricing.notes,
                    }
                )
            except CustomerPricing.DoesNotExist:
                return Response({"error": "No pricing available"}, status=404)
        else:
            # Return all customer pricing for employees
            pricing_data = []
            for pricing in CustomerPricing.objects.filter(product=product):
                pricing_data.append(
                    {
                        "customer": pricing.customer.company_name,
                        "price": pricing.price,
                        "discount_percent": pricing.discount_percent,
                        "valid_from": pricing.valid_from,
                        "valid_until": pricing.valid_until,
                    }
                )
            return Response(pricing_data)


class AssetViewSet(viewsets.ModelViewSet):
    """API ViewSet for assets"""

    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Asset.objects.filter(is_active=True)

        if self.request.user.is_customer:
            # Filter by allowed categories
            if self.request.user.allowed_asset_categories:
                queryset = queryset.filter(
                    categories__slug__in=self.request.user.allowed_asset_categories
                ).distinct()
            else:
                queryset = queryset.filter(is_public=True)

        # Apply filters
        asset_type = self.request.query_params.get("type")
        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(tags__name__icontains=search)
            ).distinct()

        return queryset

    @action(detail=True, methods=["post"])
    def download(self, request, pk=None):
        """Track asset download"""
        asset = self.get_object()

        # Log the download
        AssetDownload.objects.create(
            asset=asset,
            user=request.user,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            purpose=request.data.get("purpose", ""),
            notes=request.data.get("notes", ""),
        )

        return Response(
            {
                "download_url": asset.file.url if asset.file else None,
                "message": "Download tracked successfully",
            }
        )


class FeedViewSet(viewsets.ModelViewSet):
    """API ViewSet for feeds"""

    serializer_class = FeedSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = DataFeed.objects.select_related("customer")

        if self.request.user.is_customer:
            queryset = queryset.filter(customer=self.request.user)

        return queryset

    @action(detail=True, methods=["post"])
    def generate(self, request, pk=None):
        """Generate feed"""
        feed = self.get_object()

        # Check if there's already a pending generation
        if feed.generations.filter(status="pending").exists():
            return Response(
                {"error": "Feed generation already in progress"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create new generation
        generation = FeedGeneration.objects.create(
            feed=feed, started_by=request.user, status="pending"
        )

        # Start generation task (would use Celery in production)
        # generate_feed_task.delay(generation.id)

        return Response(
            {"generation_id": str(generation.id), "message": "Feed generation started"}
        )

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Get feed generation status"""
        feed = self.get_object()
        latest_generation = feed.generations.order_by("-started_at").first()

        if latest_generation:
            return Response(
                {
                    "generation_id": str(latest_generation.id),
                    "status": latest_generation.status,
                    "started_at": latest_generation.started_at,
                    "completed_at": latest_generation.completed_at,
                    "progress": latest_generation.progress,
                    "error_message": latest_generation.error_message,
                }
            )
        else:
            return Response({"message": "No generations found"})


# Authentication endpoints
@api_view(["POST"])
def api_login(request):
    """API login endpoint"""
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "Username and password required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)
    if user and user.is_active:
        login(request, user)
        return Response(
            {
                "user_id": user.id,
                "username": user.username,
                "role": user.role,
                "message": "Login successful",
            }
        )
    else:
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def api_logout(request):
    """API logout endpoint"""
    logout(request)
    return Response({"message": "Logout successful"})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def refresh_token(request):
    """Refresh authentication token"""
    # In a real implementation, this would refresh JWT tokens
    return Response(
        {
            "user_id": request.user.id,
            "username": request.user.username,
            "role": request.user.role,
            "message": "Token refreshed",
        }
    )


# Product endpoints
class ProductSearchView(generics.ListAPIView):
    """Search products"""

    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get("q", "")

        if len(query) < 2:
            return Product.objects.none()

        queryset = Product.objects.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(description__icontains=query)
            | Q(part_numbers__icontains=query),
            is_active=True,
        )

        if self.request.user.is_customer:
            queryset = queryset.filter(
                customer_prices__customer=self.request.user
            ).distinct()

        return queryset[:20]


class ProductFitmentAPIView(APIView):
    """Product fitment API"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Get product fitments"""
        product = get_object_or_404(Product, pk=pk)
        fitments = ProductFitment.objects.filter(product=product)

        fitment_data = []
        for fitment in fitments:
            fitment_data.append(
                {
                    "id": fitment.id,
                    "year_start": fitment.year_start,
                    "year_end": fitment.year_end,
                    "make": fitment.make,
                    "model": fitment.model,
                    "submodel": fitment.submodel,
                    "engine": fitment.engine,
                    "trim": fitment.trim,
                    "notes": fitment.notes,
                }
            )

        return Response(fitment_data)


class CustomerPricingAPIView(APIView):
    """Customer pricing API"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Get customer pricing for product"""
        product = get_object_or_404(Product, pk=pk)

        if request.user.is_customer:
            try:
                pricing = CustomerPricing.objects.get(
                    customer=request.user, product=product
                )
                return Response(
                    {
                        "price": pricing.price,
                        "discount_percent": pricing.discount_percent,
                        "valid_from": pricing.valid_from,
                        "valid_until": pricing.valid_until,
                    }
                )
            except CustomerPricing.DoesNotExist:
                return Response({"error": "No pricing available"}, status=404)
        else:
            return Response({"error": "Permission denied"}, status=403)


class BulkProductUpdateView(APIView):
    """Bulk product updates"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Bulk update products"""
        if not request.user.is_employee:
            return Response({"error": "Permission denied"}, status=403)

        product_ids = request.data.get("product_ids", [])
        action = request.data.get("action")

        if not product_ids or not action:
            return Response({"error": "product_ids and action required"}, status=400)

        products = Product.objects.filter(id__in=product_ids)
        count = products.count()

        if action == "activate":
            products.update(is_active=True)
        elif action == "deactivate":
            products.update(is_active=False)
        elif action == "feature":
            products.update(is_featured=True)
        elif action == "unfeature":
            products.update(is_featured=False)
        else:
            return Response({"error": "Invalid action"}, status=400)

        return Response({"message": f"{count} products updated", "count": count})


# Asset endpoints
class AssetUploadAPIView(APIView):
    """Asset upload API"""

    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Upload asset"""
        if not request.user.is_employee:
            return Response({"error": "Permission denied"}, status=403)

        file = request.FILES.get("file")
        if not file:
            return Response({"error": "File required"}, status=400)

        asset = Asset.objects.create(
            title=request.data.get("title", file.name),
            description=request.data.get("description", ""),
            file=file,
            asset_type=request.data.get("asset_type", "other"),
            is_public=request.data.get("is_public", False),
            created_by=request.user,
        )

        return Response(
            {
                "id": asset.id,
                "title": asset.title,
                "file_url": asset.file.url,
                "message": "Asset uploaded successfully",
            }
        )


class AssetDownloadAPIView(APIView):
    """Asset download API"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Download asset"""
        asset = get_object_or_404(Asset, pk=pk, is_active=True)

        # Check user permissions
        if request.user.is_customer:
            if request.user.allowed_asset_categories:
                if not asset.categories.filter(
                    slug__in=request.user.allowed_asset_categories
                ).exists():
                    return Response({"error": "Permission denied"}, status=403)
            elif not asset.is_public:
                return Response({"error": "Permission denied"}, status=403)

        # Log the download
        AssetDownload.objects.create(
            asset=asset,
            user=request.user,
            ip_address=request.META.get("REMOTE_ADDR", ""),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )

        return Response(
            {
                "download_url": asset.file.url if asset.file else None,
                "file_name": asset.file.name.split("/")[-1] if asset.file else None,
                "file_size": asset.file_size,
            }
        )


class AssetSearchView(generics.ListAPIView):
    """Search assets"""

    serializer_class = AssetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get("q", "")

        if len(query) < 2:
            return Asset.objects.none()

        queryset = Asset.objects.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(tags__name__icontains=query),
            is_active=True,
        ).distinct()

        if self.request.user.is_customer:
            if self.request.user.allowed_asset_categories:
                queryset = queryset.filter(
                    categories__slug__in=self.request.user.allowed_asset_categories
                ).distinct()
            else:
                queryset = queryset.filter(is_public=True)

        return queryset[:20]


# Feed endpoints
class GenerateFeedAPIView(APIView):
    """Generate feed API"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        """Generate feed"""
        feed = get_object_or_404(DataFeed, pk=pk)

        # Check permissions
        if request.user.is_customer and feed.customer != request.user:
            return Response({"error": "Permission denied"}, status=403)
        elif not request.user.is_employee and not request.user.is_customer:
            return Response({"error": "Permission denied"}, status=403)

        # Check if there's already a pending generation
        if feed.generations.filter(status="pending").exists():
            return Response(
                {"error": "Feed generation already in progress"}, status=400
            )

        # Create new generation
        generation = FeedGeneration.objects.create(
            feed=feed, started_by=request.user, status="pending"
        )

        return Response(
            {"generation_id": str(generation.id), "message": "Feed generation started"}
        )


class FeedStatusAPIView(APIView):
    """Feed status API"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        """Get feed status"""
        feed = get_object_or_404(DataFeed, pk=pk)

        # Check permissions
        if request.user.is_customer and feed.customer != request.user:
            return Response({"error": "Permission denied"}, status=403)

        latest_generation = feed.generations.order_by("-started_at").first()

        if latest_generation:
            return Response(
                {
                    "generation_id": str(latest_generation.id),
                    "status": latest_generation.status,
                    "started_at": latest_generation.started_at,
                    "completed_at": latest_generation.completed_at,
                    "progress": latest_generation.progress,
                    "error_message": latest_generation.error_message,
                }
            )
        else:
            return Response({"message": "No generations found"})


class FeedDownloadAPIView(APIView):
    """Feed download API"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, generation_id):
        """Download feed file"""
        generation = get_object_or_404(FeedGeneration, id=generation_id)

        # Check permissions
        if request.user.is_customer and generation.feed.customer != request.user:
            return Response({"error": "Permission denied"}, status=403)

        if generation.status != "completed":
            return Response({"error": "Feed generation not complete"}, status=400)

        return Response(
            {
                "download_url": generation.file.url if generation.file else None,
                "file_name": f"{generation.feed.name}_{generation.started_at.strftime('%Y%m%d_%H%M%S')}.{generation.feed.format}",
                "file_size": generation.file.size if generation.file else None,
            }
        )


# Notification endpoints
class NotificationListAPIView(generics.ListAPIView):
    """List user notifications"""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Pagination
        page_size = int(request.query_params.get("page_size", 20))
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(request.query_params.get("page", 1))

        notifications = []
        for notification in page:
            notifications.append(
                {
                    "id": notification.id,
                    "title": notification.title,
                    "message": notification.message,
                    "type": notification.notification_type,
                    "is_read": notification.is_read,
                    "action_url": notification.action_url,
                    "action_label": notification.action_label,
                    "created_at": notification.created_at,
                    "read_at": notification.read_at,
                }
            )

        return Response(
            {
                "notifications": notifications,
                "total": paginator.count,
                "page": page.number,
                "pages": paginator.num_pages,
            }
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_notification_read_api(request, pk):
    """Mark notification as read"""
    try:
        notification = Notification.objects.get(id=pk, user=request.user)
        notification.mark_as_read()
        return Response({"message": "Notification marked as read"})
    except Notification.DoesNotExist:
        return Response({"error": "Notification not found"}, status=404)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def mark_all_notifications_read_api(request):
    """Mark all notifications as read"""
    count = Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )

    return Response(
        {"message": f"{count} notifications marked as read", "count": count}
    )


# User endpoints
class UserProfileAPIView(APIView):
    """User profile API"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user profile"""
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
                "company_name": user.company_name,
                "phone": user.phone,
                "customer_number": user.customer_number,
                "is_active": user.is_active,
                "created_at": user.created_at,
            }
        )


class UserSettingsAPIView(APIView):
    """User settings API"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user settings"""
        user = request.user
        return Response(
            {
                "notification_product_updates": getattr(
                    user, "notification_product_updates", True
                ),
                "notification_price_changes": getattr(
                    user, "notification_price_changes", True
                ),
                "notification_new_assets": getattr(
                    user, "notification_new_assets", True
                ),
                "notification_feed_ready": getattr(
                    user, "notification_feed_ready", True
                ),
                "notification_system": getattr(user, "notification_system", True),
            }
        )

    def post(self, request):
        """Update user settings"""
        user = request.user

        for field, value in request.data.items():
            if field.startswith("notification_"):
                setattr(user, field, bool(value))

        user.save()
        return Response({"message": "Settings updated successfully"})


# System endpoints
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def health_check_api(request):
    """API health check"""
    return Response(
        {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "version": "1.0.0",
        }
    )


class SystemStatsAPIView(APIView):
    """System statistics API"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get system statistics"""
        if not request.user.is_employee:
            return Response({"error": "Permission denied"}, status=403)

        stats = {
            "products": {
                "total": Product.objects.count(),
                "active": Product.objects.filter(is_active=True).count(),
                "featured": Product.objects.filter(is_featured=True).count(),
            },
            "assets": {
                "total": Asset.objects.count(),
                "active": Asset.objects.filter(is_active=True).count(),
                "public": Asset.objects.filter(is_public=True).count(),
            },
            "feeds": {
                "total": DataFeed.objects.count(),
                "active": DataFeed.objects.filter(is_active=True).count(),
            },
            "users": {
                "total": User.objects.count(),
                "active": User.objects.filter(is_active=True).count(),
                "customers": User.objects.filter(role="customer").count(),
                "employees": User.objects.filter(role="employee").count(),
            },
        }

        return Response(stats)


# Webhook endpoints
class ProductUpdateWebhook(APIView):
    """Webhook for product updates from external systems"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Handle product update webhook"""
        if not request.user.is_employee:
            return Response({"error": "Permission denied"}, status=403)

        try:
            data = request.data
            _webhook_type = data.get("type", "product_update")

            # Validate required fields
            required_fields = ["product_id", "action"]
            if not all(field in data for field in required_fields):
                return Response(
                    {"error": "Missing required fields: product_id, action"}, status=400
                )

            product_id = data.get("product_id")
            action = data.get("action")  # 'create', 'update', 'delete'

            with transaction.atomic():
                if action == "create":
                    # Create new product
                    product_data = data.get("product_data", {})
                    product = Product.objects.create(
                        sku=product_data.get("sku"),
                        number=product_data.get("number"),
                        description=product_data.get("description", ""),
                        msrp=product_data.get("msrp"),
                        is_active=product_data.get("is_active", True),
                        created_by=request.user,
                    )

                    # Log the webhook action
                    AuditLog.objects.create(
                        user=request.user,
                        action="webhook_product_create",
                        model_name="Product",
                        object_id=product.id,
                        changes={"webhook_data": data},
                    )

                    return Response(
                        {
                            "message": "Product created successfully",
                            "product_id": product.id,
                        }
                    )

                elif action == "update":
                    # Update existing product
                    try:
                        product = Product.objects.get(id=product_id)
                        old_data = {
                            "sku": product.sku,
                            "number": product.number,
                            "description": product.description,
                            "msrp": product.msrp,
                            "is_active": product.is_active,
                        }

                        product_data = data.get("product_data", {})
                        if "sku" in product_data:
                            product.sku = product_data["sku"]
                        if "number" in product_data:
                            product.number = product_data["number"]
                        if "description" in product_data:
                            product.description = product_data["description"]
                        if "msrp" in product_data:
                            product.msrp = product_data["msrp"]
                        if "is_active" in product_data:
                            product.is_active = product_data["is_active"]

                        product.save()

                        # Log the webhook action
                        AuditLog.objects.create(
                            user=request.user,
                            action="webhook_product_update",
                            model_name="Product",
                            object_id=product.id,
                            changes={
                                "old_data": old_data,
                                "new_data": product_data,
                                "webhook_data": data,
                            },
                        )

                        return Response(
                            {
                                "message": "Product updated successfully",
                                "product_id": product.id,
                            }
                        )

                    except Product.DoesNotExist:
                        return Response(
                            {"error": f"Product with ID {product_id} not found"},
                            status=404,
                        )

                elif action == "delete":
                    # Soft delete product
                    try:
                        product = Product.objects.get(id=product_id)
                        product.is_active = False
                        product.save()

                        # Log the webhook action
                        AuditLog.objects.create(
                            user=request.user,
                            action="webhook_product_delete",
                            model_name="Product",
                            object_id=product.id,
                            changes={"webhook_data": data},
                        )

                        return Response(
                            {
                                "message": "Product deactivated successfully",
                                "product_id": product.id,
                            }
                        )

                    except Product.DoesNotExist:
                        return Response(
                            {"error": f"Product with ID {product_id} not found"},
                            status=404,
                        )

                else:
                    return Response({"error": f"Unknown action: {action}"}, status=400)

        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            return Response(
                {"error": "Internal server error", "details": str(e)}, status=500
            )


class InventoryUpdateWebhook(APIView):
    """Webhook for inventory updates from external systems"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Handle inventory update webhook"""
        if not request.user.is_employee:
            return Response({"error": "Permission denied"}, status=403)

        try:
            data = request.data
            _webhook_type = data.get("type", "inventory_update")

            # Validate required fields
            required_fields = ["product_id", "quantity"]
            if not all(field in data for field in required_fields):
                return Response(
                    {"error": "Missing required fields: product_id, quantity"},
                    status=400,
                )

            product_id = data.get("product_id")
            quantity = data.get("quantity")
            location = data.get("location", "default")

            with transaction.atomic():
                try:
                    product = Product.objects.get(id=product_id)

                    # Update inventory fields if they exist on the product model
                    old_quantity = getattr(product, "quantity_on_hand", 0)

                    if hasattr(product, "quantity_on_hand"):
                        product.quantity_on_hand = quantity
                    if hasattr(product, "inventory_location"):
                        product.inventory_location = location
                    if hasattr(product, "last_inventory_update"):
                        product.last_inventory_update = timezone.now()

                    product.save()

                    # Log the webhook action
                    AuditLog.objects.create(
                        user=request.user,
                        action="webhook_inventory_update",
                        model_name="Product",
                        object_id=product.id,
                        changes={
                            "old_quantity": old_quantity,
                            "new_quantity": quantity,
                            "location": location,
                            "webhook_data": data,
                        },
                    )

                    # Create notification for low inventory if needed
                    if quantity < 10:  # Low inventory threshold
                        from core.models import Notification

                        Notification.objects.create(
                            user=request.user,
                            title="Low inventory alert",
                            message=f"Product {product.sku} ({product.number}) has low inventory: {quantity} units",
                            notification_type="inventory_alert",
                        )

                    return Response(
                        {
                            "message": "Inventory updated successfully",
                            "product_id": product.id,
                            "old_quantity": old_quantity,
                            "new_quantity": quantity,
                        }
                    )

                except Product.DoesNotExist:
                    return Response(
                        {"error": f"Product with ID {product_id} not found"}, status=404
                    )

        except Exception as e:
            logger.error(f"Inventory webhook processing error: {str(e)}")
            return Response(
                {"error": "Internal server error", "details": str(e)}, status=500
            )
