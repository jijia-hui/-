-- 微服务版数据库初始化（MySQL 容器首次启动时经 /docker-entrypoint-initdb.d 执行）：
-- 同一 MySQL 实例内为三个业务微服务各建一个库（库级隔离，物理上杜绝跨服务联表）。
-- 业务账号由镜像环境变量 MYSQL_USER/MYSQL_PASSWORD 创建，这里只建库并授权。
CREATE DATABASE IF NOT EXISTS otp_user CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS otp_course CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS otp_assignment CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON otp_user.* TO 'teach_user'@'%';
GRANT ALL PRIVILEGES ON otp_course.* TO 'teach_user'@'%';
GRANT ALL PRIVILEGES ON otp_assignment.* TO 'teach_user'@'%';
FLUSH PRIVILEGES;
