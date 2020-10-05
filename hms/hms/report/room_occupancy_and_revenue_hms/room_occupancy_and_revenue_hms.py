# Copyright (c) 2013, GreyCube Technologies and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

def execute(filters=None):
    columns, data = get_columns(filters), get_data(filters)
    return columns, data


def get_data(filters):
    data = frappe.db.sql("""
with fn as     
(
   select t.*, t.no_of_rooms * days.ndays total_rooms, occ.occupancy, 
   round(occ.occupancy/days.ndays,2) avg_occupancy, 
   round(t.no_of_rooms * days.ndays - occ.occupancy,2) empty,
   round((t.no_of_rooms * days.ndays - occ.occupancy)/days.ndays, 2) avg_empty,
   std.price_list_rate normal_rate,
   spl.price_list_rate special_rate,
   round(occ.revenue, 2) revenue, 
   round(occ.revenue/days.ndays, 2) revenue_per_day, days.ndays
   from 
   (
      select rm.room_type, rm.room_type_name, rt.service_item,
      count(rm.name) no_of_rooms
      from `tabRoom HMS` rm
      inner join `tabRoom Type HMS` rt on rt.name = rm.room_type 
      group by rm.room_type
   ) t 
   cross join (select datediff(%(to_date)s,%(from_date)s)+1 ndays) days
   left outer join 
   (
      select item_code, price_list_rate, weekend_rate_cf, 
      row_number() over(PARTITION by item_code order by coalesce(valid_upto,'21000101') desc) rn
      from `tabItem Price` 
      where price_list='Standard Selling' and coalesce(valid_upto,'21000101') >  %(to_date)s
   ) std on std.rn = 1 and std.item_code = t.service_item
   left outer join 
   (
      select item_code, price_list_rate, weekend_rate_cf, 
      row_number() over(PARTITION by item_code order by coalesce(valid_upto,'21000101') desc) rn
      from `tabItem Price` 
      where price_list='Special Day Price List' and coalesce(valid_upto,'21000101') > %(to_date)s
   ) spl on spl.rn = 1 and spl.item_code = t.service_item
   left outer join 
   (
      select rt.name room_type, sum(sit.qty) occupancy, sum(base_net_amount) revenue
      from `tabSales Invoice` si
      inner join `tabSales Invoice Item` sit on sit.parent = si.name 
      inner join `tabRoom Type HMS` rt on rt.service_item =  sit.item_code 
      where si.company = %(company)s
      and si.docstatus = 1
      and si.room_date_cf BETWEEN %(from_date)s and %(to_date)s
      group by rt.name
   ) occ on occ.room_type = t.room_type
)
select * from fn
union all
select 'Total', '', '', sum(fn.no_of_rooms), sum(fn.total_rooms), sum(occupancy), 
round(sum(fn.total_rooms)/ndays,2),sum(empty), round(sum(empty/ndays),2),
0, 0, sum(revenue), round(sum(revenue)/ndays,2), ndays
from fn""", filters, as_dict=1, debug=True)

    return data


def get_columns(filters):
    return [
                dict(label="Room Type", fieldname="room_type",
             fieldtype="", width=160),
                dict(label="No of Rooms", fieldname="no_of_rooms",
             type="numericColumn", width=120),
                dict(label="Total Rooms", fieldname="total_rooms",
             type="numericColumn", width=120),
                dict(label="Occupancy", fieldname="occupancy",
             type="numericColumn", width=110),
                dict(label="Empty", fieldname="empty",
             type="numericColumn", width=90),
                dict(label="Avg Occupancy per Day", fieldname="avg_occupancy",
             type="numericColumn", width=180),
                dict(label="Avg Empty", fieldname="avg_empty",
             type="numericColumn", width=110),
                dict(label="Normal Room Rate", fieldname="normal_rate",
             type="numericColumn", width=160),
                dict(label="Special Room Rate", fieldname="special_rate",
             type="numericColumn", width=160),
                dict(label="Total Revenue", fieldname="revenue",
             type="numericColumn", width=130),
                dict(label="Avg Revenue Per Day", fieldname="revenue_per_day",
             type="numericColumn", width=180),

    ]
