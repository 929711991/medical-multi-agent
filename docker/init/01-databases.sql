CREATE DATABASE IF NOT EXISTS medical_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Checkpointer 的 JSON_TABLE 临时列使用 MySQL 8 默认排序规则，因此图数据库保持 0900 排序规则。
CREATE DATABASE IF NOT EXISTS medical_ai_graph CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
GRANT ALL PRIVILEGES ON medical_ai.* TO 'medical'@'%';
GRANT ALL PRIVILEGES ON medical_ai_graph.* TO 'medical'@'%';
FLUSH PRIVILEGES;
