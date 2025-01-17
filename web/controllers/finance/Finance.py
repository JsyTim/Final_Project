# -*- coding: utf-8 -*-
from flask import Blueprint, request, redirect, jsonify
from common.libs.Helper import ops_render
from common.models.member.Member import Member
from common.models.book.Book import Book
from common.models.pay.PayOrder import PayOrder
from common.models.pay.PayOrderItem import PayOrderItem
from application import app, db
from common.libs.UrlManager import UrlManager
from common.libs.Helper import iPagination,selectFilterObj,getDictListFilterField,getDictFilterField,getCurrentDate
from sqlalchemy import func
import json
route_finance = Blueprint('finance_page', __name__)


@route_finance.route("/index")
def index():
    resp_data = {}
    req = request.values
    page = int(req['p']) if ('p' in req and req['p']) else 1

    query = PayOrder.query

    if 'status' in req and int(req['status']) > -1:
        query = query.filter(PayOrder.status == int(req['status']))

    page_params = {
        'total': query.count(),
        'page_size': app.config['PAGE_SIZE'],
        'page': page,
        'display': app.config['PAGE_DISPLAY'],
        'url': request.full_path.replace("&p={}".format(page), "")
    }

    pages = iPagination(page_params)
    offset = (page - 1) * app.config['PAGE_SIZE']
    pay_list = query.order_by(PayOrder.id.desc()).offset(offset).limit(app.config['PAGE_SIZE']).all()
    data_list = []
    if pay_list:
        pay_order_ids = selectFilterObj(pay_list, "id")
        pay_order_items_map = getDictListFilterField(PayOrderItem, PayOrderItem.pay_order_id, "pay_order_id",
                                                     pay_order_ids)

        book_mapping = {}
        if pay_order_items_map:
            book_ids = []
            for item in pay_order_items_map:
                tmp_book_ids = selectFilterObj(pay_order_items_map[item], "book_id")
                tmp_book_ids = {}.fromkeys(tmp_book_ids).keys()
                book_ids = book_ids + list(tmp_book_ids)

            # book_ids里面会有重复的，要去重
            book_mapping = getDictFilterField(Book, Book.book_id, "book_id", book_ids)

        for item in pay_list:
            tmp_data = {
                "id": item.id,
                "status_desc": item.status_desc,
                "order_number": item.order_number,
                "price": item.total_price,
                "pay_time": item.pay_time,
                "created_time": item.created_time.strftime("%Y%m%d%H%M%S")
            }
            tmp_books = []
            tmp_order_items = pay_order_items_map[item.id]
            for tmp_order_item in tmp_order_items:
                tmp_book_info = book_mapping[tmp_order_item.book_id]
                tmp_books.append({
                    'title': tmp_book_info.book_title,
                    'quantity': tmp_order_item.quantity
                })

            tmp_data['books'] = tmp_books
            data_list.append(tmp_data)

    resp_data['list'] = data_list
    resp_data['pages'] = pages
    resp_data['search_con'] = req
    resp_data['pay_status_mapping'] = app.config['PAY_STATUS_MAPPING']
    resp_data['current'] = 'index'

    return ops_render("finance/index.html", resp_data)


@route_finance.route("/pay-info")
def payInfo():
    resp_data = {}
    req = request.values
    id = int(req['id']) if 'id' in req else 0

    reback_url = UrlManager.buildUrl("/finance/index")

    if id < 1:
        return redirect(reback_url)

    pay_order_info = PayOrder.query.filter_by(id=id).first()
    if not pay_order_info:
        return redirect(reback_url)

    member_info = Member.query.filter_by(id=pay_order_info.member_id).first()
    if not member_info:
        return redirect(reback_url)

    order_item_list = PayOrderItem.query.filter_by(pay_order_id=pay_order_info.id).all()
    data_order_item_list = []
    if order_item_list:
        book_map = getDictFilterField(Book, Book.book_id, "book_id", selectFilterObj(order_item_list, "book_id"))
        for item in order_item_list:
            tmp_book_info = book_map[item.book_id]
            tmp_data = {
                "quantity": item.quantity,
                "price": item.price,
                "title": tmp_book_info.book_title
            }
            data_order_item_list.append(tmp_data)

    address_info = {}
    if pay_order_info.express_info:
        address_info = json.loads(pay_order_info.express_info)

    resp_data['pay_order_info'] = pay_order_info
    resp_data['pay_order_items'] = data_order_item_list
    resp_data['member_info'] = member_info
    resp_data['address_info'] = address_info
    resp_data['current'] = 'index'
    return ops_render("finance/pay_info.html", resp_data)


@route_finance.route("/account")
def account():
    resp_data = {}
    req = request.values
    page = int(req['p']) if ('p' in req and req['p']) else 1
    query = PayOrder.query.filter_by(status=1)

    page_params = {
        'total': query.count(),
        'page_size': app.config['PAGE_SIZE'],
        'page': page,
        'display': app.config['PAGE_DISPLAY'],
        'url': request.full_path.replace("&p={}".format(page), "")
    }

    pages = iPagination(page_params)
    offset = (page - 1) * app.config['PAGE_SIZE']
    list = query.order_by(PayOrder.id.desc()).offset(offset).limit(app.config['PAGE_SIZE']).all()

    stat_info = db.session.query(PayOrder, func.sum(PayOrder.total_price).label("total")) \
        .filter(PayOrder.status == 1).first()

    app.logger.info(stat_info)
    resp_data['list'] = list
    resp_data['pages'] = pages
    resp_data['total_money'] = stat_info[1] if stat_info[1] else 0.00
    resp_data['current'] = 'account'
    return ops_render("finance/account.html", resp_data)


@route_finance.route("/ops", methods=["POST"])
def orderOps():
    resp = {'code': 200, 'msg': '操作成功~', 'data': {}}
    req = request.values
    id = req['id'] if 'id' in req else 0
    act = req['act'] if 'act' in req else ''
    pay_order_info = PayOrder.query.filter_by(id=id).first()
    if not pay_order_info:
        resp['code'] = -1
        resp['msg'] = "系统繁忙。请稍后再试~~"
        return jsonify(resp)

    if act == "express":
        pay_order_info.express_status = -6
        pay_order_info.updated_time = getCurrentDate()
        db.session.add(pay_order_info)
        db.session.commit()

    return jsonify(resp)

