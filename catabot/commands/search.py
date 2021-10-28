import json
import logging
import math
from typing import List, Union

from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from catabot import utils
from download_data import ALL_DATA_FILE, DATA_VERSION_FILE


NUMBERS_EMOJI = {
    1: "1️⃣",
    2: "2️⃣",
    3: "3️⃣",
    4: "4️⃣",
    5: "5️⃣",
    6: "6️⃣",
    7: "7️⃣",
    8: "8️⃣",
    9: "9️⃣",
    10: "🔟",
}

raw_data = {
    'version': None,
    'item': {},
    'uncraft': {},
    'recipe': {},
    'material': {},
    'monster': {},
    'ammunition_type': {},
    'requirement': {},
}


def _update_data():
    version = open(DATA_VERSION_FILE, 'r').read()
    if raw_data['version'] != version:
        typs = set()
        for row in json.load(open(ALL_DATA_FILE, 'r'))['data']:
            typ = _mapped_type(row['type'])
            if typ == 'item':
                if 'id' in row:
                    row_id = row['id']
                elif 'abstract' in row:
                    row_id = row['abstract']
                else:
                    logging.warning('no id and no abstract: {}', row)
                    continue
                raw_data['item'][row_id] = row
            elif typ == 'recipe':
                if 'result' in row and 'category' in row and row['category'] != 'CC_BUILDING' and \
                        ('on_display' not in row or row['on_display']):
                    if row['result'] in raw_data['recipe']:
                        raw_data['recipe'][row['result']].append(row)
                    else:
                        raw_data['recipe'][row['result']] = [row, ]
            elif typ == 'uncraft' and 'result' in row:
                if row['result'] in raw_data['uncraft']:
                    raw_data['uncraft'][row['result']].append(row)
                else:
                    raw_data['uncraft'][row['result']] = [row, ]
            elif typ == 'material':
                if 'id' in row:
                    row_id = row['id']
                elif 'abstract' in row:
                    row_id = row['abstract']
                else:
                    logging.warning('no id and no abstract: {}', row)
                    continue
                raw_data['material'][row_id] = row
            elif typ == 'monster':
                if 'id' in row:
                    row_id = row['id']
                elif 'abstract' in row:
                    row_id = row['abstract']
                else:
                    logging.warning('no id and no abstract: {}', row)
                    continue
                raw_data['monster'][row_id] = row
            elif typ == 'ammunition_type':
                raw_data['ammunition_type'][row['id']] = row
            elif typ == 'requirement':
                raw_data['requirement'][row['id']] = row
            else:
                typs.add(typ)
        # print(typs)
        for typ in {'item', 'material', 'monster'}:
            for row in raw_data[typ].values():
                if 'copy-from' in row:
                    _add_copy_from(typ, row)
                if 'volume' not in row:
                    row['volume'] = 0
                if 'weight' not in row:
                    row['weight'] = 0
        for rows_row in raw_data['recipe'].values():
            for row in rows_row:
                if 'reversible' in row and row['reversible']:
                    if row['result'] in raw_data['uncraft']:
                        raw_data['uncraft'][row['result']].append(row)
                    else:
                        raw_data['uncraft'][row['result']] = [row, ]
        raw_data['version'] = version


def _add_copy_from(typ: str, row: dict):
    if 'copy-from' in row:
        fr = raw_data[typ][row['copy-from']]
        row.pop('copy-from')
        for key in fr:
            if key not in row and key != 'abstract':
                row[key] = fr[key]
        _add_copy_from(typ, row)


def _name(row: dict) -> str:
    if 'name' in row:
        if isinstance(row['name'], str):
            return row['name']
        elif 'str' in row['name']:
            return row['name']['str']
        elif 'str_sp' in row['name']:
            return row['name']['str_sp']
    if 'id' in row:
        return row['id']
    return ''


def _names(row: dict) -> List[str]:
    names = []
    if 'name' in row:
        if isinstance(row['name'], str):
            names.append(row['name'])
        elif 'str' in row['name']:
            names.append(row['name']['str'])
        elif 'str_sp' in row['name']:
            names.append(row['name']['str_sp'])
    if 'id' in row:
        names.append(row['id'])
    return names


def _match_row(row: dict, keyword: str) -> bool:
    return any(keyword.lower() in n.lower() for n in _names(row))


def _mapped_type(typ: str) -> str:
    if typ in {"AMMO", "GUN", "ARMOR", "PET_ARMOR", "TOOL", "TOOLMOD", "TOOL_ARMOR", "BOOK",
               "COMESTIBLE", "ENGINE", "WHEEL", "GUNMOD", "MAGAZINE", "BATTERY", "GENERIC", "BIONIC_ITEM"}:
        return "item"
    elif typ == "city_building":
        return "overmap_special"
    else:
        return typ.lower()


def _search_results(typ, keyword: str) -> list:
    results = []
    for row in raw_data[typ].values():
        if 'id' in row and _match_row(row, keyword):
            results.append(row)
    return results


def _page_view(results: list, keyword: str, action: str, page: int = 1) -> (str, InlineKeyboardMarkup):
    maxpage = int(len(results) / 10)
    results = results[(page - 1) * 10: page * 10:]

    text = f"Search results for {action} {keyword}:\n\n"
    btns = []

    for i, row in enumerate(results):
        btns.append(InlineKeyboardButton(
            text=NUMBERS_EMOJI[i + 1],
            callback_data=f"cdda:{action}:{row['id']}"
        ))
        text += f"{NUMBERS_EMOJI[i + 1]} {_link_name(row['id'])}"
        if action == 'craft' and row['id'] not in raw_data['recipe']:
            text += " (can't be crafted)"
        if action == 'uncraft' and row['id'] not in raw_data['uncraft']:
            text += " (can't be disassembled)"
        text += '\n'
    text += f"\n(page {page} of {maxpage+1})"
    markup = InlineKeyboardMarkup(row_width=5)
    markup.add(*btns)
    btm_row = []
    if page > 1:
        btm_row.append(InlineKeyboardButton(text="⬅️ Prev.", callback_data=f"cdda_page{page - 1}_{action}:{keyword}"))
    btm_row.append(InlineKeyboardButton(text="❌ Cancel", callback_data="cdda_cancel"))
    if page <= maxpage:
        btm_row.append(InlineKeyboardButton(text="➡ Next️️", callback_data=f"cdda_page{page + 1}_{action}:{keyword}"))
    markup.add(*btm_row)
    return text, markup


def _parse_volume(vol: Union[str, int]) -> int:
    if not vol:
        return 0
    if isinstance(vol, int):
        return vol * 250
    try:
        if vol.lower().endswith("ml"):
            return int(vol[:-2].strip())
        if vol.lower().endswith("l"):
            return int(vol[:-1].strip()) * 1000
    except ValueError:
        logging.warning("invalid volume: {}", vol)
    return 0


def _parse_mass(weight: Union[str, int]) -> float:
    if not weight:
        return 0
    if isinstance(weight, int):
        return weight
    try:
        if weight.lower().endswith("mg"):
            return int(weight[:-2].strip()) / 1000
        if weight.lower().endswith("kg"):
            return int(weight[:-2].strip()) * 1000
        if weight.lower().endswith("g"):
            return int(weight[:-1].strip())
    except ValueError:
        logging.warning("invalid weight: {}", weight)
    return 0


def _mpa(row: dict) -> int:
    return math.floor(65 + math.floor(_parse_volume(row['volume']) / 62.5) + math.floor(_parse_mass(row['weight']) / 60.0))


def _item_length(row: dict) -> str:
    if 'longest_side' in row:
        return row['longest_side']
    return f"{round(_parse_volume(row['volume']) ** (1.0/3.0))} cm"


def _compute_to_hit(to_hit: Union[int, dict]) -> int:
    if isinstance(to_hit, int):
        return to_hit
    return -2 + {'bad': -1, 'none': 0, 'solid': 1, 'weapon': 2}[to_hit['grip']] + \
        {'hand': 0, 'short': 1, 'long': 2}[to_hit['length']] + \
        {'point': -2, 'line': -1, 'any': 0, 'every': 1}[to_hit['surface']] + \
        {'clumsy': -2, 'uneven': -1, 'neutral': 0, 'good': 1}[to_hit['balance']]


def _covers(row: dict, body_part: str) -> bool:
    if 'covers' in row:
        if body_part in row['covers']:
            return True
    if 'armor' in row:
        if any(body_part in a['covers'] for a in row['armor']):
            return True

    return False


def _part_name(part: str) -> str:
    part = part.capitalize()
    if part.endswith('_l'):
        part = "Left " + part[:-2]
    elif part.endswith('_r'):
        part = "Right " + part[:-2]
    return part


def _link_name(row_id: str) -> str:
    data = raw_data['item'][row_id]
    return f"<a href=\"https://nornagon.github.io/cdda-guide/#/item/{row_id}\">{utils.escape(_name(data))}</a>"


def _view_item(row_id: str, raw=False) -> (str, InlineKeyboardMarkup):
    # this is basically a poor copy of https://github.com/nornagon/cdda-guide/blob/main/src/types/Item.svelte
    data = raw_data['item'][row_id]
    if raw:
        text = f"<code>{json.dumps(data, indent=2)}</code>"
    else:
        text = f"{_link_name(row_id)}\n" \
               f"<i>{data['description']}</i>\n\n" \
               f"Materials: {', '.join(data['material']) if 'material' in data else 'None'}\n" \
               f"Volume: {data['volume']}\n" \
               f"Weight: {data['weight']}\n" \
               f"Length: {_item_length(data)}\n" \
               f"Flags: {', '.join(data['flags']) if 'flags' in data and len(data['flags']) > 0 else 'None'}\n"
        # TODO: flags' descriptions
        # TODO: ammo
        # TODO: faults
        if 'qualities' in data:
            # TODO: qualities' names
            text += f"Qualities: {str(data['qualities'])}\n"
        # TODO: vehicle parts
        # TODO: ascii_picture

        # TODO: if data['type'] == 'BOOK'
        if data['type'] in {'ARMOR', 'TOOL_ARMOR'}:
            text += "\nArmor:\n"
            text += "Covers: "
            covers = ""
            if _covers(data, "head"):
                covers += "The head. "
            if _covers(data, "eyes"):
                covers += "The eyes. "
            if _covers(data, "mouth"):
                covers += "The mouth. "
            if _covers(data, "torso"):
                covers += "The torso. "
            for sg, pl in [("arm", "arms"), ("hand", "hands"), ("leg", "legs"), ("foot", "feet")]:
                if 'sided' in data and data['sided'] and (_covers(data, sg+'_l') or _covers(data, sg+'_r')):
                    covers += f"Either {sg}. "
                elif _covers(data, sg+'_l') and _covers(data, sg+'_r'):
                    covers += f"The {pl}. "
                elif _covers(data, sg+'_l'):
                    covers += f"The left {sg}. "
                elif _covers(data, sg+'_r'):
                    covers += f"The right {sg}. "
            if not covers:
                covers = "Nothing."
            text += covers + '\n'
            text += "Layer: "
            flags = data['flags'] if 'flags' in data else []
            if 'PERSONAL' in flags:
                text += "Personal aura"
            elif 'SKINTIGHT' in flags:
                text += "Close to skin"
            elif 'BELTED' in flags:
                text += "Strapped"
            elif 'OUTER' in flags:
                text += "Outer"
            elif 'WAIST' in flags:
                text += "Waist"
            elif 'AURA' in flags:
                text += "Outer aura"
            else:
                text += "Normal"
            text += f"\nWarmth: {data['warmth'] if 'warmth' in data else 0}\n"
            if 'armor' in data:
                text += "Encumbrance:\n"
                for apd in data['armor']:
                    text += f"{', '.join(map(_part_name, apd['covers']))}: "
                    text += str(apd['encumbrance']) if isinstance(apd['encumbrance'], int) else \
                        f"{apd['encumbrance'][0]} ({apd['encumbrance'][1]} when full)"
                    text += "\n"
            else:
                text += f"Encumbrance: {data['encumbrance'] if 'encumbrance' in data else 0}"
                if 'max_encumbrance' in data:
                    text += f" ({data['max_encumbrance']} when full)"
                text += "\n"

            text += "Coverage: "
            if 'armor' in data:
                text += '\n'
                for apd in data['armor']:
                    text += f"{', '.join(map(_part_name, apd['covers']))}: "
                    text += f"{apd['coverage'] if 'coverage' in apd else 0}%\n"
            else:
                text += f"{data['coverage'] if 'coverage' in data else 0}\n"
            if 'environmental_protection' in data or ('material' in data and len(data['material']) > 0):
                text += "Protection:\n"
                env = data['environmental_protection'] if 'environmental_protection' in data else 0
                thickness = data['material_thickness'] if 'material_thickness' in data else 0
                if 'material' in data:
                    materials = [data['material']] if isinstance(data['material'], str) else data['material']

                    def _resist_sum(r) -> int:
                        return sum(raw_data['material'][m][r] for m in materials if r in raw_data['material'][m])

                    bash = (_resist_sum('bash_resist') * thickness) / len(materials)
                    cut = (_resist_sum('cut_resist') * thickness) / len(materials)
                    bullet = (_resist_sum('bullet_resist') * thickness) / len(materials)
                    acid = _resist_sum('acid_resist') / len(materials)
                    fire = _resist_sum('fire_resist') / len(materials)
                    if env < 10:
                        acid *= env / 10
                        fire *= env / 10
                    text += f"Bash: {bash:.2}\n"
                    text += f"Cut: {cut:.2}\n"
                    text += f"Ballistic: {bullet:.2}\n"
                    text += f"Acid: {acid:.2}\n"
                    text += f"Fire: {fire:.2}\n"
                text += f"Environmental: {env}\n"

        if data['type'] in {'TOOL', 'TOOL_ARMOR'} and (
            'charges_per_use' in data or 'power_draw' in data or 'turns_per_charge' in data or 'sub' in data
        ):
            text += "\nTool:\n"
            if 'charges_per_use' in data:
                text += f"Charges Per Use: {data['charges_per_use']}\n"
            if 'power_draw' in data:
                text += f"Power Draw: {data['power_draw'] / 1000:.1} W\n"
            if 'turns_per_charge' in data:
                text += f"Turns Per Charge: {data['turns_per_charge']}\n"
            if 'sub' in data:
                text += f"Substitute: {_link_name(data['sub'])}\n"

        # TODO: if data['type'] == 'ENGINE'
        if data['type'] == 'COMESTIBLE':
            text += "\nComestible:\n"
            text += f"Calories: {data['calories'] if 'calories' in data else 0} kcal\n"
            text += f"Quench: {data['quench'] if 'quench' in data else 0}\n"
            text += f"Enjoyability: {data['fun'] if 'fun' in data else 0}\n"
            text += f"Portions: {data['charges'] if 'charges' in data else 1}\n"
            text += f"Spoils In: {data['spoils_in'] if 'spoils_in' in data else 'never'}\n"
            text += f"Health: {data['healthy'] if 'healthy' in data else 0}\n"
            text += f"Vitamins: {', '.join(f'{v}: {p}%' for v, p in data['vitamins']) if 'vitamins' in data else 'None'}\n"

        # TODO: if data['type'] == 'WHEEL'
        # TODO: if 'seed_data' in data

        if 'bashing' in data or 'cutting' in data or data['type'] in {"GUN", "AMMO"}:
            text += "\nMelee:\n"
            text += f"Bash: {data['bashing'] if 'bashing' in data else 0}\n"
            if 'flags' in data and ('SPEAR' in data['flags'] or 'STAB' in data['flags']):
                text += "Pierce: "
            else:
                text += "Cut: "
            text += str(data['cutting'] if 'cutting' in data else 0)
            text += f"\nTo Hit: {_compute_to_hit(data['to_hit']) if 'to_hit' in data else 0}"
            text += f"\nMoves Per Attack: {_mpa(data)}\n"
            if 'techniques' in data:
                text += f"Techniques: {str(data['techniques'])}\n"

        if 'pocket_data' in data and any(data['pocket_data']):
            text += "\nPockets:\n" if len(data['pocket_data']) > 1 else '\n'
            for pocket in data['pocket_data']:
                pocket_type = pocket['pocket_type'] if 'pocket_type' in pocket else 'CONTAINER'
                if pocket_type in {'MAGAZINE', 'MAGAZINE_WELL'}:
                    text += "<b>Magazine:</b>\n"
                elif pocket_type == 'SOFTWARE':
                    text += "<b>Software</b>\n"
                elif pocket_type == 'EBOOK':
                    text += "<b>E-Book</b>\n"
                else:
                    text += "<b>Container:</b>\n"
                pocket_data = []
                if pocket_type == 'CONTAINER':
                    if 'max_contains_weight' in pocket and 'max_contains_volume' in pocket:
                        pocket_data.append(f"Max: {pocket['max_contains_volume']} / {pocket['max_contains_weight']}")
                    elif 'max_contains_volume' in pocket:
                        pocket_data.append(f"Max: {pocket['max_contains_volume']}")
                    elif 'max_contains_weight' in pocket:
                        pocket_data.append(f"Max: {pocket['max_contains_weight']}")
                    if 'max_item_length' in pocket:
                        if any(pocket_data):
                            pocket_data[0] += ' / ' + pocket['max_item_length']
                        else:
                            pocket_data.append(f"Max: {pocket['max_item_length']}")

                    if 'min_item_volume' in pocket:
                        pocket_data.append(f"Min Volume: {pocket['min_item_volume']}")

                    if 'sealed_data' in pocket and 'spoil_multiplier' in pocket['sealed_data'] \
                            and pocket['sealed_data']['spoil_multiplier'] != 1:
                        pocket_data.append(f"Spoil Multiplier: {pocket['sealed_data']['spoil_multiplier']}")

                    specials = []
                    if 'fire_protection' in pocket and pocket['fire_protection']:
                        specials.append("Fire Protection")
                    if 'watertight' in pocket and pocket['watertight']:
                        specials.append("Watertight")
                    if 'airtight' in pocket and pocket['airtight']:
                        specials.append("Airtight")
                    if 'open_container' in pocket and pocket['open_container']:
                        specials.append("Open Container")
                    if 'rigid' in pocket and pocket['rigid']:
                        specials.append("Rigid")
                    if 'holster' in pocket and pocket['holster']:
                        specials.append("Holster")
                    if any(specials):
                        pocket_data.append(f"Specials: {', '.join(specials)}")

                if 'moves' in pocket or pocket_type == 'CONTAINER':
                    pocket_data.append(f"Moves To Remove Item: {pocket['moves'] if 'moves' in pocket else 100}")

                if 'ammo_restriction' in pocket:
                    ammos = []
                    for ammo_id, max_charges in pocket['ammo_restriction'].items():
                        ammos.append(f"{max_charges} {'round' if data['type'] == 'GUN' else 'charge'}"
                                     f"{'s' if max_charges > 1 else ''} of {raw_data['ammunition_type'][ammo_id]['name']}")
                    pocket_data.append(f"Supported Ammo Types: {' / '.join(ammos)}")
                if 'flag_restriction' in pocket:
                    items = []
                    for item in raw_data['item'].values():
                        if 'flags' in item:
                            for flag in pocket['flag_restriction']:
                                if flag in item['flags']:
                                    items.append(_name(item))
                                    break
                    pocket_data.append(f"Supported Magazines: {' / '.join(items)}")
                if 'item_restriction' in pocket:
                    items = []
                    for item_id in pocket['item_restriction']:
                        items.append(_name(raw_data['item'][item_id]))
                    pocket_data.append(f"Supported Magazines: {' / '.join(items)}")
                text += '\n'.join(pocket_data) + '\n'

    markup = InlineKeyboardMarkup()
    buttons = [
        InlineKeyboardButton("👀 Description", callback_data=f"cdda:view:{row_id}")
        if raw else
        InlineKeyboardButton('🔣 Raw JSON', callback_data=f"cdda:item_raw:{row_id}")
    ]
    if row_id in raw_data['recipe']:
        buttons.append(InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}"))
    if row_id in raw_data['uncraft']:
        buttons.append(InlineKeyboardButton("🛠 Disassemble", callback_data=f"cdda:uncraft:{row_id}"))
    markup.add(*buttons)
    return text, markup


def _craft_item(row_id, raw=False, typ='recipe') -> (str, InlineKeyboardMarkup):
    if row_id not in raw_data[typ]:
        text = f"{_link_name(row_id)} " \
               f"can't be {'crafted' if typ == 'recipe' else 'disassembled'}!"
        markup = InlineKeyboardMarkup()
        buttons = [InlineKeyboardButton("👀 Description", callback_data=f"cdda:view:{row_id}")]
        if typ == 'recipe' and row_id in raw_data['uncraft']:
            buttons.append(InlineKeyboardButton("🛠 Disassemble", callback_data=f"cdda:uncraft:{row_id}"))
        if typ == 'uncraft' and row_id in raw_data['recipe']:
            buttons.append(InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}"))
        markup.add(*buttons)
        return text, markup

    datas = raw_data[typ][row_id]
    if raw:
        text = f"<code>{json.dumps(datas, indent=2)}</code>"
        if len(text) > 4096:
            text = f"<code>{str(datas)}</code>"[:4096]
    else:
        text = f"{'Craft' if typ == 'recipe' else 'Uncraft'} recipe{'s' if len(datas) > 1 else ''} for " \
               f"{_link_name(row_id)}\n\n"
        for data in datas:
            text += f"Primary skill: {data['skill_used'] if 'skill_used' in data else 'None'} " \
                    f"({data['difficulty'] if 'difficulty' in data else 0})\n"
            skills_required = []
            if 'skills_required' in data and any(data['skills_required']):
                if isinstance(data['skills_required'][0], list):
                    skills_required = data['skills_required']
                else:
                    skills_required = [data['skills_required']]
            skills_required = [f"{s} ({n})" for s, n in skills_required]
            if any(skills_required):
                text += f"Other skills: {' and '.join(skills_required)}\n"

            # TODO: proficiencies
            if 'proficiencies' in data:
                text += f"Proficiencies: {str(data['proficiencies'])}\n"
            text += f"Time to Complete: {data['time'] if 'time' in data else '0 m'}\n"
            # TODO: activity levels
            text += f"Activity Level: {data['activity_level'] if 'activity_level' in data else 'MODERATE_EXERCISE'}\n"
            if typ == 'recipe':
                text += "Batch Time Saving: "
                if 'batch_time_factors' in data:
                    text += f"{data['batch_time_factors'][0]}% at >{data['batch_time_factors'][1]} " \
                            f"unit{'s' if data['batch_time_factors'][1] > 1 else ''}\n"
                else:
                    text += "None\n"
                if 'charges' in data:
                    # TODO: need to check result type
                    text += f"Recipe Makes: {data['charges']}\n"
                if 'delete_flags' in data:
                    text += f"Delete Flags: {', '.join(data['delete_flags'])}\n"
            if 'flags' in data:
                text += f"Flags: {', '.join(data['flags'])}\n"

            tools, qualities, components = _normalize_tools(data)

            if any(tools) or any(qualities):
                text += "Tools Required:\n"
                if any(qualities):
                    for q in qualities:
                        amount = q['amount'] if 'amount' in q else 1
                        # TODO: quality name
                        text += f"- {str(amount) + ' ' if amount > 1 else ''}tool{'s' if amount > 1 else ''} " \
                                f"with {q['id']} of {q['level']} or more\n"
                if any(tools):
                    for tool in tools:
                        tool_names = []
                        for tool_id, charges in tool:
                            tool_names.append(f"{_link_name(tool_id)}" + (f" ({charges})" if charges > 0 else ''))
                        text += f"- {' OR '.join(tool_names)}\n"
            if any(components):
                text += "Components:\n"
                for components_row in components:
                    components_names = []
                    for item_id, count in components_row:
                        if item_id in raw_data['item']:
                            components_names.append(f"{count} {_link_name(item_id)}")
                    text += f"- {' OR '.join(components_names)}\n"

            if typ == 'recipe':
                if 'byproducts' in data:
                    text += "Byproducts:\n"
                    for b in data['byproducts']:
                        text += f"- {b[1] if len(b) > 1 else 1} {_link_name(b[0])}\n"

                text += "Autolearn: "
                if 'autolearn' in data:
                    if not data['autolearn']:
                        text += "No\n"
                    else:
                        skills = []
                        if isinstance(data['autolearn'], list):
                            for skill, level in data['autolearn']:
                                skills.append((skill, level))
                        else:
                            if 'skill_used' in data:
                                skills.append((data['skill_used'], data['difficulty'] if 'difficulty' in data else 0))
                            if 'skills_required' in data:
                                for skill, level in data['skills_required']:
                                    skills.append((skill, level))
                        if any(skills):
                            text += ', '.join(f"{skill} ({level})" for skill, level in skills) + '\n'
                        else:
                            text += "At Birth\n"
                else:
                    text += "No\n"

                if 'book_learn' in data:
                    books = []
                    if isinstance(data['book_learn'], list):
                        books = data['book_learn']
                    else:
                        for book_id, book_data in data['book_learn'].items():
                            books.append((book_id, book_data['skill_level']))
                    books = map(lambda r: f"{_link_name(r[0])} (at level {r[1]})", books)
                    text += f"Written In: {', '.join(books)}\n"

            text += '\n'

    markup = InlineKeyboardMarkup()
    buttons = [(
            InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}")
            if raw else
            InlineKeyboardButton('🔣 Raw JSON', callback_data=f"cdda:craft_raw:{row_id}")
        ) if typ == 'recipe' else (
            InlineKeyboardButton("🛠 Disassemble", callback_data=f"cdda:uncraft:{row_id}")
            if raw else
            InlineKeyboardButton('🔣 Raw JSON', callback_data=f"cdda:uncraft_raw:{row_id}")
        ),
        InlineKeyboardButton("👀 Description", callback_data=f"cdda:view:{row_id}"),
    ]
    if typ == 'recipe' and row_id in raw_data['uncraft']:
        buttons.append(InlineKeyboardButton("🛠 Disassemble", callback_data=f"cdda:uncraft:{row_id}"))
    if typ == 'uncraft' and row_id in raw_data['recipe']:
        buttons.append(InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}"))
    markup.add(*buttons)
    return text, markup


def _normalize_tools(data: dict) -> (list, list, list):
    tools = data['tools'] if 'tools' in data else []
    qualities = data['qualities'] if 'qualities' in data else []
    components = data['components'] if 'components' in data else []
    for components_row in components:
        for component in components_row:
            if len(component) == 3 and component[2] == 'LIST':
                req_id, count, _ = component
                components_row.remove(component)
                req = raw_data['requirement'][req_id]
                _, _, c = _normalize_tools(req)
                for r in c[0]:
                    if len(r) == 2:
                        r[1] *= count
                        components_row.append(r)
                    else:
                        req_id, count2, _ = r
                        req = raw_data['requirement'][req_id]
                        _, _, c = _normalize_tools(req)
                        for r in c[0]:
                            if len(r) == 2:
                                r[1] *= count * count2
                                components_row.append(r)
                            else:
                                logging.warning("third level of this shit! {} / {}", data, r)
    for tool_row in tools:  # TODO: idk why but fake tools (like basecamp ones) doesnt appear here
        for tool in tool_row:
            if len(tool) == 3 and tool[2] == 'LIST':
                req_id, count, _ = tool
                tool_row.remove(tool)
                req = raw_data['requirement'][req_id]
                t, _, _ = _normalize_tools(req)
                tool_row += map(lambda r: [r[0], r[1] * count], t[0])
    if 'using' in data:
        for req_id, count in data['using']:
            req = raw_data['requirement'][req_id]
            t, q, c = _normalize_tools(req)
            qualities += q
            for tr in t:
                for r in tr:
                    r[1] *= count
            tools += t
            for cr in c:
                for r in cr:
                    r[1] *= count
            components += c
    # TODO: sum

    return tools, qualities, components


def _action_view(action: str, row_id: str) -> (str, InlineKeyboardMarkup):
    if action == 'view':
        return _view_item(row_id)
    elif action == 'item_raw':
        return _view_item(row_id, True)
    elif action == 'craft':
        return _craft_item(row_id)
    elif action == 'craft_raw':
        return _craft_item(row_id, True)
    elif action == 'uncraft':
        return _craft_item(row_id, typ='uncraft')
    elif action == 'uncraft_raw':
        return _craft_item(row_id, True, typ='uncraft')
    # TODO: uncraft view
    # TODO: monster view

    typ = 'item'
    if action == 'monster':
        typ = 'monster'
    elif action == 'craft':
        typ = 'recipe'
    elif action == 'uncraft':
        typ = 'uncraft'

    markup = InlineKeyboardMarkup()
    buttons = []
    if action == 'view':
        if row_id in raw_data['recipe']:
            buttons.append(InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}"))
        if row_id in raw_data['uncraft']:
            buttons.append(InlineKeyboardButton("🛠 Disassemble", callback_data=f"cdda:uncraft:{row_id}"))
    elif action == 'craft':
        buttons.append(InlineKeyboardButton("👀 Description", callback_data=f"cdda:view:{row_id}"))
        if row_id in raw_data['uncraft']:
            buttons.append(InlineKeyboardButton("🛠 Disassemble", callback_data=f"cdda:uncraft:{row_id}"))
    elif action == 'uncraft':
        buttons.append(InlineKeyboardButton("👀 Description", callback_data=f"cdda:view:{row_id}"))
        if row_id in raw_data['recipe']:
            buttons.append(InlineKeyboardButton("🛠 Craft", callback_data=f"cdda:craft:{row_id}"))
    markup.add(*buttons)

    data = raw_data[typ][row_id]
    return f"<code>{json.dumps(data, indent=2)}</code>", markup


def search(bot: TeleBot, message: Message):
    bot.send_chat_action(message.chat.id, 'typing')
    _update_data()
    keyword = utils.get_keyword(message)
    command = utils.get_command(message).lower()
    if not keyword:
        bot.reply_to(message, f"Usage example:\n<code>{command} glazed tenderloins</code>", parse_mode='html')
        return

    action = 'view'
    typ = 'item'
    # TODO: use match
    if command in {'/c', '/craft'}:
        action = 'craft'
    elif command in {'/disassemble', '/d', '/disasm'}:
        action = 'uncraft'
    elif command in {'/m', '/mob', '/monster'}:
        action = 'monster'
        typ = 'monster'

    tmp_message = bot.reply_to(message, "Loading search results...")

    results = _search_results(typ, keyword)
    if len(results) == 0:
        bot.send_sticker(message.chat.id, 'CAADAgADxgADOtDfAeLvpRcG6I1bFgQ', message.message_id)
    elif len(results) == 1:
        text, markup = _action_view(action, results[0]['id'])
        bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')
    else:
        text, markup = _page_view(results, keyword, action)
        bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')

    utils.delete_message(bot, tmp_message)


def btn_pressed(bot: TeleBot, message: Message, data: str):
    if data.startswith('cdda:'):
        bot.send_chat_action(message.chat.id, 'typing')
        _update_data()
        utils.delete_message(bot, message)
        action, row_id = data[5::].split(':')
        text, markup = _action_view(action, row_id)
        bot.reply_to(message.reply_to_message, text, reply_markup=markup, parse_mode='HTML')
    elif data == 'cdda_cancel':
        bot.edit_message_text(message.text.split('\n')[0] + '\n(canceled)', message.chat.id, message.message_id)
    elif data.startswith('cdda_page'):
        _update_data()
        page, actkey = data[9::].split('_')
        action, keyword = actkey.split(':')
        page = int(page)
        if page < 1:
            return
        typ = 'item'
        if action == 'monster':
            typ = 'monster'
        results = _search_results(typ, keyword)
        text, markup = _page_view(results, keyword, action, page=page)
        bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup, parse_mode='HTML')
