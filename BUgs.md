1 -> Ao atualizar, ele volta a puxar os processos cancelados juntos, algum problema na atualização.
2 -> O sistema pode atualizar a cada 60 segundos, mas buscar lá do banco, pode ser a cada  5 minutos ( a requisição + pegar da tabela ), para evitar tantas requisições.

3 -> ícones ainda estão bugados, talvez vamos mudar para um MD ou MDI para simplificar, ao invés de usar SVG.

4 -> a página de gerenciar páginas está quebrada. "TypeError: index() got an unexpected keyword argument 'permissions'"