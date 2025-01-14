"""djLint add indentation to html."""

from functools import partial

import regex as re

from ..helpers import is_ignored_block_closing, is_ignored_block_opening
from ..settings import Config
from .attributes import format_attributes


def indent_html(rawcode: str, config: Config) -> str:
    """Indent raw code."""
    rawcode_flat_list = re.split("\n", rawcode)

    indent = config.indent

    beautified_code = ""
    indent_level = 0
    is_raw_first_line = False
    is_block_raw = False

    slt_html = config.indent_html_tags

    # here using all tags cause we allow empty tags on one line
    always_self_closing_html = config.always_self_closing_html_tags

    # here using all tags cause we allow empty tags on one line
    slt_template = config.optional_single_line_template_tags

    for item in rawcode_flat_list:
        # if a raw tag first line
        if not is_block_raw and is_ignored_block_opening(config, item):
            is_raw_first_line = True

        # if a raw tag then start ignoring
        if is_ignored_block_opening(config, item):
            is_block_raw = True

        if re.findall(
            config.ignored_inline_blocks, item, flags=re.IGNORECASE | re.VERBOSE
        ):
            tmp = (indent * indent_level) + item + "\n"

        # if a one-line, inline tag, just process it, only if line starts w/ it
        elif (
            re.findall(
                fr"(<({slt_html})>)(.*?)(</(\2)>)", item, re.IGNORECASE | re.VERBOSE
            )
            or re.findall(
                fr"(<({slt_html})[ ].+?>)(.*?)(</(\2)>)",
                item,
                re.IGNORECASE | re.VERBOSE,
            )
            or re.findall(
                fr"^({{%[ ]*?({slt_template})[ ]+?.+?%}})(.*?)({{%[ ]+?end(\2)[ ]+?.*?%}})",
                item,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            )
            or re.findall(
                fr"(<({slt_html})[ ].*?/>)", item, flags=re.IGNORECASE | re.VERBOSE
            )
            or re.findall(
                fr"(<({always_self_closing_html})[ ].*?/?>)",
                item,
                flags=re.IGNORECASE | re.VERBOSE,
            )
        ) and is_block_raw is False:
            tmp = (indent * indent_level) + item + "\n"

        # if unindent, move left
        elif (
            re.search(
                config.tag_unindent,
                item,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            )
            and is_block_raw is False
            or re.search(config.ignored_block_closing, item, re.IGNORECASE | re.VERBOSE)
        ):
            indent_level = max(indent_level - 1, 0)
            tmp = (indent * indent_level) + item + "\n"

        elif (
            re.search(
                r"^" + str(config.tag_unindent_line),
                item,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            )
            and is_block_raw is False
        ):
            tmp = (indent * (indent_level - 1)) + item + "\n"

        # if indent, move right
        elif (
            re.search(
                r"^(?:" + str(config.tag_indent) + r")",
                item,
                re.IGNORECASE | re.MULTILINE | re.VERBOSE,
            )
            and is_block_raw is False
        ):
            tmp = (indent * indent_level) + item + "\n"
            indent_level = indent_level + 1

        elif is_raw_first_line is True:
            tmp = (indent * indent_level) + item + "\n"

        elif is_block_raw is True:
            tmp = item + "\n"

        # if just a blank line
        elif item.strip() == "":
            tmp = item.strip()

        # otherwise, just leave same level
        else:
            tmp = (indent * indent_level) + item + "\n"

        # we can try to fix template tags. ignore handlebars
        if config.profile not in ["handlebars", "golang"]:
            tmp = re.sub(r"({[{|%]\-?)(\w[^}].+?)([}|%]})", r"\1 \2\3", tmp)
            tmp = re.sub(r"({[{|%])([^}].+?[^(?:\ |\-)])([}|%]})", r"\1\2 \3", tmp)
            tmp = re.sub(r"({[{|%])([^}].+?[^ ])(\-[}|%]})", r"\1\2 \3", tmp)

        elif config.profile == "handlebars":
            # handlebars templates
            tmp = re.sub(r"({{#(?:each|if).+?[^ ])(}})", r"\1 \2", tmp)

        # if a opening raw tag then start ignoring.. only if there is no closing tag
        # on the same line
        if is_ignored_block_opening(config, item):
            is_block_raw = True
            is_raw_first_line = False

        # if a normal tag, we can try to expand attributes
        elif (
            config.format_long_attributes
            and is_block_raw is False
            and len(tmp) > int(config.max_line_length)
        ):
            # get leading space, and attributes
            func = partial(format_attributes, config)
            tmp = re.sub(
                re.compile(
                    fr"(\s*?)(<\w+\s)((?:{config.attribute_pattern}|\s*?)+?)(/?>)",
                    re.VERBOSE | re.IGNORECASE,
                ),
                func,
                tmp,
            )

        # turn off raw block if we hit end - for one line raw blocks, but not an inline raw
        if is_ignored_block_closing(config, item):
            is_block_raw = False

        beautified_code = beautified_code + tmp

    # should we add blank lines after load tags?
    if config.blank_line_after_tag:
        for tag in [x.strip() for x in config.blank_line_after_tag.split(",")]:
            beautified_code = re.sub(
                re.compile(
                    fr"((?:{{%\s*?{tag}[^}}]+?%}}\n?)+)",
                    re.IGNORECASE | re.MULTILINE | re.DOTALL,
                ),
                r"\1\n",
                beautified_code,
            )

    return beautified_code.strip() + "\n"
