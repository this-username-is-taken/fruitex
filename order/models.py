from django.db import models
from django.utils.timezone import localtime

from datetime import date

from order import managers

class Invoice(models.Model):
  def __unicode__(self):
    return self.invoice_num

  def _get_total(self):
    return self.subtotal + self.tax + self.delivery - self.discount;

  # Payment methods
  PAYMENT_METHODS_PAYPAL = 'PP'
  PAYMENT_METHODS_SQUARE = 'SQ'
  PAYMENT_METHODS = (
    (PAYMENT_METHODS_PAYPAL, 'Paypal'),
    (PAYMENT_METHODS_SQUARE, 'On delivery (Square)'),
  )

  # Status
  STATUS_PENDING = 'PEND'
  STATUS_PAID = 'PAID'
  STATUS_FLAGGED = 'FLAG'
  STATUS_CANCELLED = 'CANC'
  STATUSES = (
    (STATUS_PENDING, 'Pending'),
    (STATUS_PAID, 'Paid'),
    (STATUS_FLAGGED, 'Flagged'),
    (STATUS_CANCELLED, 'Cancelled'),
  )

  invoice_num = models.CharField(max_length=64, unique=True)
  payment_method = models.CharField(max_length=2, choices=PAYMENT_METHODS, default=PAYMENT_METHODS_PAYPAL)
  status = models.CharField(max_length=4, choices=STATUSES)
  payer = models.CharField(max_length=256, blank=True)
  when_created = models.DateTimeField(auto_now_add=True)
  when_updated = models.DateTimeField(auto_now=True)
  coupon = models.ForeignKey('Coupon', blank=True, null=True)

  # Amounts
  subtotal = models.DecimalField(max_digits=16, decimal_places=2)
  tax = models.DecimalField(max_digits=16, decimal_places=2)
  delivery = models.DecimalField(max_digits=16, decimal_places=2)
  discount = models.DecimalField(max_digits=16, decimal_places=2)
  total = property(_get_total)

  # Customer
  customer_name = models.CharField(max_length=64)
  address = models.TextField()
  postcode = models.CharField(max_length=16)
  phone = models.CharField(max_length=16)
  email = models.EmailField(max_length=256)
  user = models.ForeignKey('auth.User', blank=True, null=True, related_name='invoices', on_delete=models.SET_NULL)


class DeliveryWindow(models.Model):
  def __unicode__(self):
    start = localtime(self.start)
    end = localtime(self.end)
    return start.strftime(self.DATETIME_FORMAT) + " ~ " + end.strftime(self.DATETIME_FORMAT)

  DATETIME_FORMAT = '%a %b %d  %H:%M'

  store = models.ForeignKey('shop.Store', related_name='delivery_windows')
  start = models.DateTimeField()
  end = models.DateTimeField()

  objects = managers.DeliveryWindowManager()


class OrderItem(models.Model):
  def __unicode__(self):
    return str(self.item) + ' * ' + str(self.quantity)

  order = models.ForeignKey('Order')
  item = models.ForeignKey('shop.Item')
  quantity = models.IntegerField()
  allow_sub = models.BooleanField()
  item_cost = models.DecimalField(max_digits=16, decimal_places=2)
  item_tax = models.DecimalField(max_digits=16, decimal_places=2)


class Order(models.Model):
  def __unicode__(self):
    return '#' + str(self.id)

  def _get_order_items(self):
    return OrderItem.objects.filter(order__id=self.id)

  # Status
  STATUS_PENDING = 'PEND'                 # Pending until invoice has been paid
  STATUS_WAITING = 'WAIT'                 # Waiting for the delivery time
  STATUS_PURCHASED = 'PURC'               # Item's has been purchased and packed
  STATUS_ON_THE_WAY = 'ONTW'              # Delivery on its way
  STATUS_DELIVERED = 'DELI'               # Order delivered
  STATUSES = (
    (STATUS_PENDING, 'Pending'),
    (STATUS_WAITING, 'Waiting'),
    (STATUS_PURCHASED, 'Purchased'),
    (STATUS_ON_THE_WAY, 'On the way'),
    (STATUS_DELIVERED, 'Delivered'),
  )

  # Order
  items = models.ManyToManyField('shop.Item', related_name='orders', through=OrderItem)
  order_items = property(_get_order_items)
  subtotal = models.DecimalField(max_digits=16, decimal_places=2)
  tax = models.DecimalField(max_digits=16, decimal_places=2)
  delivery_window = models.ForeignKey('DeliveryWindow', related_name='orders', on_delete=models.PROTECT)

  # Metas
  invoice = models.ForeignKey('Invoice', related_name='orders', on_delete=models.PROTECT)
  status = models.CharField(max_length=4, choices=STATUSES)
  when_created = models.DateTimeField(auto_now_add=True)
  when_updated = models.DateTimeField(auto_now=True)


class Coupon(models.Model):
  def __unicode__(self):
    return self.code

  # Coupon types
  TYPE_FIXED_AMOUNT = 'FIX'
  TYPE_PERCENTAGE = 'PERC'
  TYPES = (
    (TYPE_FIXED_AMOUNT, 'Fixed amount'),
    (TYPE_PERCENTAGE, 'Percentage'),
  )

  objects = managers.CouponManager()

  code = models.CharField(max_length=32, unique=True)
  type = models.CharField(max_length=4, choices=TYPES)
  value = models.DecimalField(max_digits=16, decimal_places=2)
  used = models.BooleanField()
  expire = models.DateField(blank=True, default=date.max)
