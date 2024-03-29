#!/usr/bin/env python3

# pip3 install pyquery aiohttp Pillow

import argparse
import json
import re

import MySQLdb
from jsonc_parser.parser import JsoncParser

parser = argparse.ArgumentParser(description='')

parser.add_argument('--import-items',
                    action='store',
                    nargs='?',
                    default='./items.json',
                    type=str,
                    help='import items.json')

args = parser.parse_args()

def main(args: dict):
    try:
        config: dict = JsoncParser.parse_file("../config.jsonc")
    except Exception as ex:
        print("[FATAL]", ex)
        raise ex

    item_list = {}
    with open(args.import_items, "r", encoding="utf-8") as fp:
        item_list = json.load(fp)

    if len(item_list) == 0:
        print("[FATAL]", "item_list is None")
        exit(0)

    try:
        connection = MySQLdb.connect(**config["mysql"])
        connection.autocommit(False)

        select_query = """
            SELECT item_name
            FROM item_suggest_tbl_tmp
            ORDER BY 1 ASC
            ;
        """

        update_query = """
            UPDATE item_suggest_tbl_tmp
            SET item_id = %s, description = %s
            WHERE item_name = %s
            ;
        """

        item_db: list = []
        item_db_ids: list[tuple] = []
        with connection.cursor() as cursor:
            cursor.execute(select_query)
            item_db = [item[0] for item in cursor.fetchall()]

        pattern_slot = re.compile(r"^.+\[(\d+)\]$")
        for item_name in item_db:
            item_id: int = None
            displayname: str = re.sub("^(.+)\[(\d+|製造)\]$", r"\1", item_name)
            match_slot = pattern_slot.search(item_name)

            for key, values in item_list.items():
                if values["displayname"] == displayname:
                    if match_slot:
                        slot_num: int = int(match_slot.group(1))
                        if "slot" not in values and slot_num == 0:
                            item_id = int(key)
                            break
                        elif "slot" in values and values["slot"] == slot_num:
                            item_id = int(key)
                            break
                        else:
                            item_id = int(key)
                            #not break
                    else:
                        item_id = int(key)
                        break

            if item_id is None:
                print("[WARNING]", "Not found item_name:", item_name)
            else:
                description: str = item_list[str(item_id)]["description"]
                item_db_ids.append((item_id, description, item_name))

        with connection.cursor() as cursor:
            cursor.executemany(update_query, item_db_ids)

        connection.commit()

    except Exception as ex:
        raise ex
    finally:
        if connection is not None:
            connection.close()

if __name__ == '__main__':
    main(args)
