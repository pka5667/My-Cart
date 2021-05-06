import json
from math import ceil

from django.shortcuts import render
from django.http import HttpResponse
from .models import Product, ContactUsMessage, Order, OrderUpdate
from django.views.decorators.csrf import csrf_exempt
from .Paytm import checkSum

MERCHANT_KEY = 'gnHrUoU!B9La3#fX'


# Create your views here.
def index(request):
    # products = Product.objects.all()
    # allProducts = [[products, range(1, numSlides), numSlides],
    #                [products, range(1, numSlides), numSlides]]
    allProducts = []
    category_and_Products_id = Product.objects.values("category", 'id')
    uniqueCategories = {item['category'] for item in category_and_Products_id}
    for catg in uniqueCategories:
        product = Product.objects.filter(category=catg)
        n = len(product)
        numSlides = n // 4 if (n % 4 == 0) else ((n // 4) + 1)
        allProducts.append([product, range(1, numSlides), numSlides])
    params = {'allProducts': allProducts}
    return render(request, "shop/index.html", params)


def about(request):
    return render(request, "shop/about.html")


def contact(request):
    formSubmitted = "No"
    if request.method == 'POST':
        try:
            name = request.POST.get('name', default='')
            email = request.POST.get('email', default='')
            phone = request.POST.get('phone', default='')
            textarea = request.POST.get('txtarea', default='')

            contactModel = ContactUsMessage(name=name, email=email, phone=phone, description=textarea)
            contactModel.save()

            formSubmitted = "True"
        except:
            formSubmitted = "False"

    params = {
        'formSubmitted': formSubmitted
    }

    return render(request, "shop/contact.html", params)


def tracker(request):
    if request.method == 'POST':
        orderId = request.POST.get('order_id')
        email = request.POST.get('email')
        try:
            order = Order.objects.filter(order_id=orderId, email=email)
            if len(order) > 0:
                updates_objects = OrderUpdate.objects.filter(order_id=orderId)
                updates = []
                for item in updates_objects:
                    updates.append({"update_description": item.update_description, "timeStamp": item.timeStamp})
                response = json.dumps([updates, order[0].items_JSON], default=str)
                return HttpResponse(response)
            else:
                return HttpResponse('{}')
        except Exception as e:
            return HttpResponse('{}')
    return render(request, "shop/tracker.html")


def searchMatch(query, item):
    if query in item.product_name.lower() or query in item.category.lower() or query in item.subcategory.lower() or query in item.product_description.lower():
        return True
    return False


def search(request):
    query = (request.GET.get('search')).lower()
    allProducts = []
    category_and_Products_id = Product.objects.values("category", 'id')
    uniqueCategories = {item['category'] for item in category_and_Products_id}
    for catg in uniqueCategories:
        temp_product = Product.objects.filter(category=catg)
        product = [item for item in temp_product if searchMatch(query, item)]
        n = len(product)
        numSlides = n // 4 + ceil(n / 4 - n // 4)
        if len(product) > 0:
            allProducts.append([product, range(1, numSlides), numSlides])
    params = {'allProducts': allProducts}
    return render(request, "shop/search.html", params)


def productView(request, myid):
    # fetch the product using id
    product = Product.objects.filter(id=myid)  # it always gives an array
    params = {
        'product': product[0]
    }
    return render(request, "shop/productView.html", params)


def checkout(request):
    orderPlaced = "No"
    params = {'orderPlaced': orderPlaced}
    if request.method == 'POST':
        try:
            items_JSON = request.POST.get('items_JSON', default='')
            amount = request.POST.get('amount', default='')
            name = request.POST.get('name', default='')
            email = request.POST.get('email', default='')
            phone = request.POST.get('phone', default=0)
            address = request.POST.get('address1', default='')
            city = request.POST.get('city', default='')
            state = request.POST.get('state', default='')
            zip_code = request.POST.get('zip_code', default='')

            order = Order(items_JSON=items_JSON, amount=amount, name=name, email=email, phone=phone, address=address,
                          city=city,
                          state=state,
                          zip_code=zip_code)
            order.save()
            orderPlaced = "True"
            update = OrderUpdate(order_id=order.order_id, update_description="Order Placed")
            update.save()
            params = {'orderPlaced': orderPlaced, 'order_id': order.order_id}

            # return render(request, "shop/checkout.html", params)
            # request Paytm to transfer the amount to your account after payment by user
            param_dict = {
                'MID': 'BYmFRr72500820404276',
                'ORDER_ID': str(order.order_id),
                'TXN_AMOUNT': str(amount),
                'CUST_ID': email,
                'INDUSTRY_TYPE_ID': 'Retail',
                'WEBSITE': 'WEBSTAGING',
                'CHANNEL_ID': 'WEB',
                'CALLBACK_URL': "http://pka5667-my-cart.herokuapp.com/shop/handlerequest"
            }
            param_dict['CHECKSUMHASH'] = checkSum.generate_checksum(param_dict, MERCHANT_KEY)
            return render(request, "shop/paytm.html", {'param_dict': param_dict})
        except Exception as e:
            orderPlaced = "False"
            params = {'orderPlaced': orderPlaced}

    return render(request, "shop/checkout.html", params)


@csrf_exempt  # so that website can handel request from another website also (here we want request from Paytm)
def handleRequest(request):
    # Paytm will send post request here
    form = request.POST
    print(form)
    checkSumHash = form['CHECKSUMHASH']
    response_dict = {}
    for i in form.keys():
        response_dict[i] = form[i]
    varify = checkSum.verify_checksum(response_dict, MERCHANT_KEY, checkSumHash)
    if varify and form['RESPCODE'] == "01":
        # print("Payment successful")
        orderPlaced = "True"
        saveOrder = Order.objects.get(order_id=response_dict['ORDERID'])
        saveOrder.paymentStatus = 'Success'
        update = OrderUpdate(order_id=response_dict['ORDERID'], update_description="Payment Success")
        update.save()
        saveOrder.save()
    else:
        # print("Payment failed due to " + response_dict['RESPMSG'])
        orderPlaced = "False"
        saveOrder = Order.objects.get(order_id=response_dict['ORDERID'])
        saveOrder.paymentStatus = 'Failed'
        saveOrder.save()
    params = {'orderPlaced': orderPlaced, 'order_id': response_dict['ORDERID']}
    return render(request, "shop/checkout.html", params)
