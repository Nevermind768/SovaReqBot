"""Длины соответсвующих полей в одноимённых таблицах.
"""


class UserLen:
    BAN_REASON = 50


class UserInfoLen:
    FULLNAME = 50
    CONTACT = 50


class AppLen:
    CATEGORY = 50
    ADDRESS = 50
    BODY = 4000
    POLICE = 512
    ATTACHMENTS = 1024


class AttachmentLen:
    HASH = 50
    LINK = 128
