export function versionLabel(value) {
  const text = String(value ?? "").trim();
  if (/^(published|latest version)$/i.test(text)) return "Latest Version";
  const numeric = /^(?:v(?:ersion)?\s*)?(\d+(?:\.\d+)*)$/i.exec(text);
  return numeric ? `V ${numeric[1]}` : text || "—";
}

export function comparisonLabel(item) {
  const name = item.comparison_name || item.comparisonName || item.name || item.title;
  if (name) {
    return name.replace(/\(([^()]*)\s+vs\s+([^()]*)\)$/i, (_, source, target) =>
      `(${versionLabel(source)} vs ${versionLabel(target)})`);
  }
  const source = item.source_version ?? item.old_revision ?? item.source_revision;
  const target = item.target_version ?? item.new_revision ?? item.target_revision;
  const pair = `${versionLabel(source)} vs ${versionLabel(target)}`;
  if (item.page_name) return `${item.page_name} (${pair})`;
  return source != null || target != null ? pair : "Version comparison";
}