from rest_framework import serializers
from .models import User, Category, Product, Cart, CartItem, Order, OrderItem, Payment

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'address', 'created_at']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent']


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'description', 'price', 'stock_quantity', 'category', 'image_url', 'created_at']


class CartItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    product_details = ProductSerializer(source='product', read_only=True)

    def get_total_price(self, obj):
        return obj.quantity * obj.product.price

    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product', 'product_details', 'quantity', 'added_at', 'total_price']


class CartSerializer(serializers.ModelSerializer):
    cartitem_set = CartItemSerializer(many=True)
    total_cart_amount = serializers.SerializerMethodField()

    def get_total_cart_amount(self, obj):
        return sum(item.quantity * item.product.price for item in obj.cartitem_set.all())

    class Meta:
        model = Cart
        fields = ['id', 'user', 'created_at', 'cartitem_set', 'total_cart_amount']


class OrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    product_details = serializers.SerializerMethodField()

    def get_product_details(self, obj):
        if obj.cart_item and obj.cart_item.product:
            return {
                'name': obj.cart_item.product.name,
                'price': str(obj.cart_item.product.price),
                'image_url': obj.cart_item.product.image_url
            }
        return None

    def get_total_price(self, obj):
        if obj.cart_item and obj.cart_item.product:
            return obj.quantity * obj.price
        return 0

    class Meta:
        model = OrderItem
        fields = ['id', 'order', 'cart_item', 'product_details', 'quantity', 'price', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    order_set = OrderItemSerializer(many=True, read_only=True)
    total_order_amount = serializers.SerializerMethodField()

    def get_total_order_amount(self, obj):
        return sum(item.quantity * item.price for item in obj.order_set.all() if item.cart_item and item.cart_item.product)

    class Meta:
        model = Order
        fields = ['id', 'user', 'total_amount', 'status', 'created_at', 'order_set', 'total_order_amount']

    def create(self, validated_data):
        user = validated_data.get('user')
        cart = Cart.objects.filter(user=user).first()
        
        if not cart or not cart.cartitem_set.exists():
            raise serializers.ValidationError("Корзина пуста")
        
        # Создаем заказ
        order = Order.objects.create(
            user=user,
            total_amount=sum(item.quantity * item.product.price for item in cart.cartitem_set.all()),
            status='pending'
        )
        
        # Создаем элементы заказа из корзины
        for cart_item in cart.cartitem_set.all():
            OrderItem.objects.create(
                order=order,
                cart_item=cart_item,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
        
        # Очищаем корзину после создания заказа
        cart.cartitem_set.all().delete()
        
        return order


class PaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Payment
        fields = ['id', 'order', 'payment_method', 'payment_status', 'paid_at']