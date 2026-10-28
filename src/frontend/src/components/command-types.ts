export interface CommandItem {
  id: string
  title: string
  group: string
  hint?: string
  keywords?: string
  to?: string
  action?: () => void
}

export function filterCommands(commands: CommandItem[], query: string): CommandItem[] {
  const keyword = query.trim().toLowerCase()
  if (!keyword) return commands
  return commands.filter((item) =>
    [item.title, item.group, item.hint, item.keywords]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(keyword)),
  )
}
