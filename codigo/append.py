def merge_idempotente(existentes, novos, chave):
    vistos = {tuple(str(r[k]) for k in chave) for r in existentes}
    out = list(existentes)
    for r in novos:
        k = tuple(str(r[c]) for c in chave)
        if k not in vistos:
            vistos.add(k)
            out.append(r)
    return out


def delta_idempotente(existentes, novos, chave):
    """Linhas de `novos` cuja chave ainda NÃO existe em `existentes` (o que seria adicionado)."""
    vistos = {tuple(str(r[k]) for k in chave) for r in existentes}
    return [r for r in novos if tuple(str(r[c]) for c in chave) not in vistos]
