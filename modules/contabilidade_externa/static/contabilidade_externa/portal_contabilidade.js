(function() {
    const detalhesModal = document.getElementById('modalDetalhes');
    const baixaModal = document.getElementById('modalBaixa');
    const detalhesConteudo = document.getElementById('detalhesConteudo');
    const observacaoInput = document.getElementById('observacaoBaixa');
    const eventoBaixaId = document.getElementById('eventoBaixaId');
    const btnConfirmarBaixa = document.getElementById('btnConfirmarBaixa');

    const detalhesModalInstance = detalhesModal ? new bootstrap.Modal(detalhesModal) : null;
    const baixaModalInstance = baixaModal ? new bootstrap.Modal(baixaModal) : null;

    const filtroTipo = document.getElementById('filtroTipoEvento');
    const filtroBusca = document.getElementById('filtroBuscaPendencias');
    const btnLimparFiltros = document.getElementById('btnLimparFiltros');
    const mensagemSemResultados = document.getElementById('filtroSemResultados');
    const tabelaPendencias = document.getElementById('tabelaPendenciasContabilidade');

    function formatarData(dataIso) {
        if (!dataIso) {
            return '-';
        }
        try {
            const data = new Date(dataIso);
            return data.toLocaleDateString('pt-BR');
        } catch (error) {
            return dataIso;
        }
    }

    function formatarDataHora(dataIso) {
        if (!dataIso) {
            return '-';
        }
        try {
            const data = new Date(dataIso);
            return data.toLocaleString('pt-BR');
        } catch (error) {
            return dataIso;
        }
    }

    function formatarMoeda(valor) {
        if (valor === null || valor === undefined || valor === '') {
            return '-';
        }

        const numero = Number(String(valor).replace(/[^0-9,-]+/g, '').replace(',', '.'));
        if (Number.isNaN(numero)) {
            return valor;
        }

        return numero.toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        });
    }

    function obterEventoDaLinha(linha) {
        if (!linha) {
            return null;
        }

        if (!linha.__eventoCache) {
            const dataset = linha.getAttribute('data-evento');
            if (dataset) {
                try {
                    linha.__eventoCache = JSON.parse(dataset);
                } catch (error) {
                    console.warn('Não foi possível converter dataset do evento', error);
                    linha.__eventoCache = null;
                }
            }
        }

        return linha.__eventoCache;
    }

    function montarDetalhes(evento) {
        if (!detalhesConteudo || !evento) {
            return;
        }

        const colaborador = evento.colaborador || {};
        const empresa = evento.empresa || {};
        const cargo = evento.cargo || {};
        const departamento = evento.departamento || {};
        const dadosAdicionais = evento.dados_adicionais || {};

        const salarioAnterior = dadosAdicionais.salario_anterior || dadosAdicionais.salarioAnterior;
        const cargoAnterior = dadosAdicionais.cargo_anterior_nome || dadosAdicionais.cargo_anterior || dadosAdicionais.cargo_anterior_id;
        const eventosComComparativo = ['Promoção', 'Alteração Salarial', 'Ajuste Salarial', 'Reajuste'];
        const exibirComparativo = salarioAnterior || cargoAnterior || eventosComComparativo.includes(evento.tipo_evento);

        const observacaoContabil = evento.obs_contabilidade || dadosAdicionais.obs_contabilidade;

        detalhesConteudo.innerHTML = `
            <section class="info-section">
                <h6><i class="mdi mdi-account"></i> Colaborador</h6>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Nome</span>
                        <strong>${colaborador.nome_completo || '-'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">CPF</span>
                        <strong>${colaborador.cpf || '-'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Matrícula</span>
                        <strong>${colaborador.matricula || 'Sem matrícula'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Data de nascimento</span>
                        <strong>${formatarData(colaborador.data_nascimento)}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">PIS</span>
                        <strong>${colaborador.pis_pasep || '-'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">E-mail corporativo</span>
                        <strong>${colaborador.email_corporativo || '-'}</strong>
                    </div>
                </div>
            </section>

            <section class="info-section">
                <h6><i class="mdi mdi-calendar-check"></i> Evento a validar</h6>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Tipo de evento</span>
                        <strong>${evento.tipo_evento || '-'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Data do evento</span>
                        <strong>${formatarData(evento.data_evento)}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Status contábil</span>
                        <strong>${evento.status_contabilidade || '-'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Descrição / Motivo</span>
                        <strong>${evento.descricao_e_motivos || '-'}</strong>
                    </div>
                </div>
            </section>

            <section class="info-section">
                <h6><i class="mdi mdi-office-building"></i> Informações corporativas</h6>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Empresa</span>
                        <strong>${empresa.razao_social || '-'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Departamento</span>
                        <strong>${departamento.nome_departamento || '-'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Cargo atual</span>
                        <strong>${cargo.nome_cargo || '-'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Salário atual</span>
                        <strong>${formatarMoeda(evento.salario_mensal)}</strong>
                    </div>
                </div>
            </section>

            ${exibirComparativo ? `
            <section class="info-section">
                <h6><i class="mdi mdi-chart-line"></i> Histórico do evento</h6>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Salário anterior</span>
                        <strong>${formatarMoeda(salarioAnterior)}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Novo salário</span>
                        <strong>${formatarMoeda(evento.salario_mensal)}</strong>
                    </div>
                    ${cargoAnterior ? `
                    <div class="info-item">
                        <span class="info-label">Cargo anterior</span>
                        <strong>${cargoAnterior}</strong>
                    </div>
                    ` : ''}
                </div>
            </section>
            ` : ''}

            <section class="info-section">
                <h6><i class="mdi mdi-account-check"></i> Contabilidade</h6>
                <div class="info-grid">
                    <div class="info-item">
                        <span class="info-label">Observações contábeis</span>
                        <strong>${observacaoContabil || '—'}</strong>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Última atualização</span>
                        <strong>${formatarDataHora(evento.updated_at)}</strong>
                    </div>
                </div>
            </section>
        `;
    }

    function localizarEvento(eventoId) {
        const linha = document.querySelector(`tr[data-evento-id="${eventoId}"]`);
        if (linha) {
            return obterEventoDaLinha(linha);
        }

        if (Array.isArray(window.__PENDENCIAS__)) {
            return window.__PENDENCIAS__.find((item) => item.id === eventoId);
        }
        return null;
    }

    function atualizarBadgePendencias(totalVisivel) {
        const badge = document.querySelector('.badge.bg-primary-subtle');
        const linhas = document.querySelectorAll('tbody tr[data-evento-id]');
        if (badge) {
            const quantidade = typeof totalVisivel === 'number' ? totalVisivel : linhas.length;
            const texto = `${quantidade} pendência${quantidade === 1 ? '' : 's'} aberta${quantidade === 1 ? '' : 's'}`;
            badge.innerHTML = `<i class="mdi mdi-timer-sand"></i> ${texto}`;
        }

        if (Array.isArray(window.__PENDENCIAS__)) {
            window.__PENDENCIAS__ = window.__PENDENCIAS__.filter((item) => {
                return document.querySelector(`tr[data-evento-id="${item.id}"]`) !== null;
            });
        }
    }

    function aplicarFiltros() {
        if (!tabelaPendencias) {
            return;
        }

        const linhas = tabelaPendencias.querySelectorAll('tbody tr[data-evento-id]');
        const tipoSelecionado = filtroTipo ? filtroTipo.value : '';
        const termoBusca = (filtroBusca ? filtroBusca.value : '').trim().toLowerCase();
        let visiveis = 0;

        linhas.forEach((linha) => {
            const evento = obterEventoDaLinha(linha) || {};
            let visivel = true;

            if (tipoSelecionado && evento.tipo_evento !== tipoSelecionado) {
                visivel = false;
            }

            if (visivel && termoBusca) {
                const campoPesquisa = [
                    evento.tipo_evento,
                    evento.status_contabilidade,
                    evento.empresa_nome,
                    evento.departamento_nome,
                    evento.cargo_nome,
                    evento.colaborador?.nome_completo,
                    evento.colaborador?.cpf,
                    evento.colaborador?.matricula
                ]
                    .filter(Boolean)
                    .join(' ') 
                    .toLowerCase();

                if (!campoPesquisa.includes(termoBusca)) {
                    visivel = false;
                }
            }

            linha.style.display = visivel ? '' : 'none';
            if (visivel) {
                visiveis += 1;
            }
        });

        if (mensagemSemResultados) {
            mensagemSemResultados.style.display = visiveis === 0 ? 'block' : 'none';
        }

        atualizarBadgePendencias(visiveis);

        const linhasTotais = tabelaPendencias.querySelectorAll('tbody tr[data-evento-id]').length;
        if (linhasTotais === 0) {
            const wrapper = document.getElementById('listaPendenciasWrapper');
            if (wrapper) {
                wrapper.innerHTML = `
                    <div class="empty-state text-center py-5">
                        <i class="mdi mdi-check-circle-outline"></i>
                        <h5>Todas as pendências foram concluídas</h5>
                        <p>Assim que o RH registrar novos eventos, eles aparecerão por aqui.</p>
                    </div>
                `;
            }
        }
    }

    function limparFiltros() {
        if (filtroTipo) {
            filtroTipo.value = '';
        }
        if (filtroBusca) {
            filtroBusca.value = '';
        }
        aplicarFiltros();
    }

    async function concluirEvento() {
        const eventoId = eventoBaixaId ? eventoBaixaId.value : '';
        if (!eventoId) {
            alert('Evento não identificado.');
            return;
        }

        btnConfirmarBaixa.disabled = true;
        btnConfirmarBaixa.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processando...';

        try {
            const response = await fetch(`/portal-contabilidade/api/eventos/${eventoId}/concluir`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    observacao: observacaoInput ? observacaoInput.value : ''
                })
            });

            const data = await response.json();

            if (!data.success) {
                alert(data.message || 'Não foi possível concluir o evento.');
                return;
            }

            if (baixaModalInstance) {
                baixaModalInstance.hide();
            }

            const linha = document.querySelector(`tr[data-evento-id="${eventoId}"]`);
            if (linha) {
                linha.remove();
            }

            aplicarFiltros();
            alert('✅ Evento concluído com sucesso!');
        } catch (error) {
            console.error('Erro ao concluir evento', error);
            alert('Erro inesperado ao concluir o evento. Tente novamente.');
        } finally {
            btnConfirmarBaixa.disabled = false;
            btnConfirmarBaixa.innerHTML = '<i class="mdi mdi-check"></i> Confirmar baixa';
            if (observacaoInput) {
                observacaoInput.value = '';
            }
            if (eventoBaixaId) {
                eventoBaixaId.value = '';
            }
        }
    }

    function configurarEventosTabela() {
        const detalhesBotoes = document.querySelectorAll('.btn-detalhes');
        detalhesBotoes.forEach((botao) => {
            botao.addEventListener('click', () => {
                const eventoId = botao.getAttribute('data-evento-id');
                const evento = localizarEvento(eventoId);
                if (!evento) {
                    alert('Não foi possível carregar os detalhes deste evento.');
                    return;
                }
                montarDetalhes(evento);
                if (detalhesModalInstance) {
                    detalhesModalInstance.show();
                }
            });
        });

        const concluirBotoes = document.querySelectorAll('.btn-concluir');
        concluirBotoes.forEach((botao) => {
            botao.addEventListener('click', () => {
                const eventoId = botao.getAttribute('data-evento-id');
                if (eventoBaixaId) {
                    eventoBaixaId.value = eventoId;
                }
                if (observacaoInput) {
                    observacaoInput.value = '';
                }
                if (baixaModalInstance) {
                    baixaModalInstance.show();
                }
            });
        });
    }

    if (btnConfirmarBaixa) {
        btnConfirmarBaixa.addEventListener('click', concluirEvento);
    }

    configurarEventosTabela();

    if (filtroTipo) {
        filtroTipo.addEventListener('change', aplicarFiltros);
    }
    if (filtroBusca) {
        filtroBusca.addEventListener('input', aplicarFiltros);
    }
    if (btnLimparFiltros) {
        btnLimparFiltros.addEventListener('click', (event) => {
            event.preventDefault();
            limparFiltros();
        });
    }

    aplicarFiltros();
})();
