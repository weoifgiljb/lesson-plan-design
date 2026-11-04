-- 0010：回填任务归属组
--
-- 0007 加了 group_name 列，但 insert_task 当时没写它，历史任务全是空串，
-- 导致"组长建的任务组内教师可见"失效。这里按任务创建者所在教研组回填。

UPDATE task
SET group_name = COALESCE((SELECT u.group_name FROM user u WHERE u.id = task.owner_id), '')
WHERE group_name = '';
