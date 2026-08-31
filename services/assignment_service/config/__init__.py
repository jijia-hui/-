# PyMySQL 兼容 mysqlclient（Django MySQL 后端）；与单体版 web_backend 保持一致
import pymysql

pymysql.install_as_MySQLdb()
