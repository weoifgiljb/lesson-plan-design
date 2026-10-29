-- 0008：回填历史同步事件
--
-- 0003 只建表，没有为升级前已存在的版本/已删除教案补事件，导致升级后
-- `GET /sync/pull?since=0` 拿不到历史数据（插件端会以为本地已同步）。
-- 这里按创建时间一次性补齐，并且幂等（已有事件不重复插入）。

INSERT INTO sync_event (kind, plan_id, plan_version_id, created_at)
SELECT 'version', pv.plan_id, pv.id, pv.created_at
FROM plan_version pv
WHERE NOT EXISTS (
    SELECT 1 FROM sync_event e WHERE e.plan_version_id = pv.id
);

INSERT INTO sync_event (kind, plan_id, plan_version_id, created_at)
SELECT 'deleted', p.id, NULL, p.deleted_at
FROM plan p
WHERE p.deleted_at IS NOT NULL
  AND NOT EXISTS (
      SELECT 1 FROM sync_event e WHERE e.plan_id = p.id AND e.kind = 'deleted'
  );
