from bcsv_reader import BCSV
from msbt_reader import MSBT
from binascii import hexlify
from os import listdir
import sys, string, codecs
'''reload(sys)
sys.setdefaultencoding('utf8')'''

msg_path = "../message1.1"
bcsv_path = "."
output_name = "scrape_data_test.txt"

def getindices(s):
    return [i for i, c in enumerate(s) if c.isupper()]

#grab item ids and names
item_strings = []
item_id2str = {}
item_str2id = {}
for filename in listdir(msg_path + "/String_USen/Item/"):
    if filename.endswith(".msbt"):
        labels, text = MSBT().read_msbt("%s/String_USen/Item/%s" % (msg_path, filename))
        labels2 = []
        for entry in labels: #take from 3D groups to 2D array
            for entry2 in entry:
                labels2.append(entry2)
        labels2.sort(key=lambda x: x[1]) #sort by text index
        for entry in labels2:
            if not entry[0].endswith(b"_pl"): #filter out plural
                itemid = int(entry[0].split(b"_")[1]) #Rug_07322 -> 7322
                itemname = text[entry[1]][0]
                item_strings.append([itemid, itemname])
                item_id2str[itemid] = itemname
                item_str2id[itemname] = itemid

#grab clothing ids and names
cloth_strings = []
cloth_id2str = {}
cloth_str2id = {}
for filename in listdir(msg_path + "/String_USen/Outfit/GroupName/"):
    if filename.endswith(".msbt"):
        labels, text = MSBT().read_msbt("%s/String_USen/Outfit/GroupName/%s" % (msg_path, filename))
        labels2 = []
        for entry in labels: #take from 3D groups to 2D array
            for entry2 in entry:
                labels2.append(entry2)
        labels2.sort(key=lambda x: x[1]) #sort by text index
        for entry in labels2:
            itemid = int(entry[0])
            itemname = text[entry[1]][0]
            cloth_strings.append([itemid, itemname])
            cloth_id2str[itemid] = itemname
            cloth_str2id[itemname] = itemid

#convert cloth_itemid -> item_itemid
cloth_data = BCSV().read_bcsv(bcsv_path + "/ItemClothGroup.bcsv")
cloth_lookup = {}
cloth_lookup2 = {}
cloth_data2 = []
for entry in cloth_data:
    clothid  = entry[0x54706054] #string id
    itemid   = entry[0x65503F9F] #item id
    itemname = entry[0x13AB5198].decode("UTF-8").rstrip(u"\0").encode("UTF-8") #TODO: assert at end?
    itemdesc = entry[0x036E8EBE].decode("UTF-8").rstrip(u"\0").encode("UTF-8")
    cloth_lookup[clothid] = itemid
    cloth_lookup2[itemname] = itemid
    cloth_data2.append([clothid, itemid, itemname, itemdesc])

#add clothes to item_strings to add in next step, skip if 
for entry in cloth_data2:
    try: #store the string names that match, we'll extrapolate later
        item_strings.append([entry[1], cloth_id2str[entry[0]]])
    except: pass

#create lookup table for everything
item_lookup = {}
for entry in item_strings:
    item_lookup[entry[0]] = entry[1]

#parse table for IDs and filenames
item_data = BCSV().read_bcsv(bcsv_path + "/ItemParam.bcsv")
item_table = []
do_later = []
dupe_lookup = {}
skipme = False
with open(output_name, "wb") as o:
    o.write(b"Item ID (hex), Buy Price, Sell Price, Item Name, item_type, file_name, file_desc\r\n")
    for entry in item_data:
        item_id = entry[0x54706054]
        buy_price = entry[0x718B024D]
        sell_price = int(buy_price / 4.0)
        file_name = entry[0x3FEBC642].decode("UTF-8").rstrip(u"\0").encode("UTF-8")
        item_type = entry[0xFC275E86].decode("UTF-8").rstrip(u"\0").encode("UTF-8")
        try:
            file_desc = entry[0xB8CC232C].decode("UTF-8").rstrip(u"\0").encode("UTF-8")
        except: #bcsv stupid limit, 0x40 truncated string
            file_desc = b"FILE_DESC_TRUNCATED " + entry[0xB8CC232C].decode("UTF-8", "ignore").encode("UTF-8")

        try:
            item_name = item_lookup[item_id] #check if we have the name for that id, else do_later
            item_table.append([item_id, buy_price, sell_price, item_name, item_type, file_name, file_desc])
            dupe_lookup[file_name.rstrip(string.digits)] = item_name #store base for most stuff, e.g. 0, 1, 2 of thing needs to be looked up
            indices = getindices(file_name) #strip end of string so e.g. TwotoneMonotone + variants
            #o.write("%04X, %d, %d, %s, %s, %s, %s\r\n" % (item_id, buy_price, sell_price, item_name.encode("UTF-8"), item_type, file_name, file_desc))
            if len(indices) > 1 and len(file_name[:indices[-1]]) > 5:
                dupe_lookup[file_name[:indices[-1]]] = item_name #store item name for color variants
        except:
            do_later.append([item_id, buy_price, sell_price, item_type, file_name, file_desc])
    for entry in do_later:
        file_name = entry[4]
        try:
            item_name = dupe_lookup[file_name.rstrip(string.digits)]
        except:
            try: 
                indices = getindices(file_name)
                item_name = dupe_lookup[file_name[:indices[-1]]]
            except: item_name = b"UNUSED"
        print("%s %s" % (entry[4], item_name.encode("UTF-8")))
        item_table.append([entry[0], entry[1], entry[2], item_name, entry[3], entry[4], entry[5]])
    item_table.sort(key=lambda x: x[0]) #sort by item_id
    for entry in item_table:
        o.write("%04X, %d, %d, %s, %s, %s, %s\r\n" % (entry[0], entry[1], entry[2], entry[3].encode("UTF-8"), entry[4], entry[5], entry[6]))
