(function() {
    const detalhesModal = document.getElementById('modalDetalhes');
    const baixaModal = document.getElementById('modalBaixa');
    const detalhesConteudo = document.getElementById('detalhesConteudo');
    const observacaoInput = document.getElementById('observacaoBaixa');
    const eventoBaixaId = document.getElementById('eventoBaixaId');
    const btnConfirmarBaixa = document.getElementById('btnConfirmarBaixa');

    const detalhesModalInstance = detalhesModal ? new bootstrap.Modal(detalhesModal) : null;
    const baixaModalInstance = baixaModal ? new bootstrap.Modal(baixaModal) : null;

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

    function montarDetalhes(evento) {
        if (!detalhesConteudo || !evento) {
            return;
        }

        const colaborador = evento.colaborador || {};
        const empresa = evento.empresa || {};
        const cargo = evento.cargo || {};
        const departamento = evento.departamento || {};

        const cards = [];

        cards.push(`
            <div class="detalhe-card">
                <h6>Colaborador</h6>
                <p><strong>${colaborador.nome_completo || '-'} </strong></p>
                <p><small>CPF: </small>${colaborador.cpf || '-'}<br>
                <small>Matrícula: </small>${colaborador.matricula || '-'}<br>
                <small>E-mail: </small>${colaborador.email_corporativo || '-'}</p>
            </div>
        `);

        cards.push(`
            <div class="detalhe-card">
                <h6>Evento</h6>
                <p><strong>${evento.tipo_evento || '-'} </strong></p>
                <p><small>Data do evento: </small>${formatarData(evento.data_evento)}<br>
                <small>Status contábil: </small>${evento.status_contabilidade || '-'}<br>
                <small>Descrição/Motivos: </small>${evento.descricao_e_motivos || '-'}</p>
            </div>
        `);

        cards.push(`
            <div class="detalhe-card">
                <h6>Informações adicionais</h6>
                <p><small>Empresa: </small>${empresa.razao_social || '-'}<br>
                <small>Cargo: </small>${cargo.nome_cargo || '-'}<br>
                <small>Departamento: </small>${departamento.nome_departamento || '-'}<br>
                <small>Salário atual: </small>${evento.salario_mensal || '-'}<br>
                <small>Observações contabilidade: </small>${evento.obs_contabilidade || '-'}<br>
                <small>Última atualização: </small>${formatarDataHora(evento.updated_at)}</p>
            </div>
        `);

        detalhesConteudo.innerHTML = cards.join('');
    }

    function localizarEvento(eventoId) {
        const linha = document.querySelector(`tr[data-evento-id="${eventoId}"]`);
        if (linha) {
            const dataset = linha.getAttribute('data-evento');
            if (dataset) {
                try {
                    return JSON.parse(dataset);
                } catch (error) {
                    console.warn('Não foi possível converter dataset do evento', error);
                }
            }
        }

        if (Array.isArray(window.__PENDENCIAS__)) {
            return window.__PENDENCIAS__.find((item) => item.id === eventoId);
        }
        return null;
    }

    function atualizarBadgePendencias() {
        const badge = document.querySelector('.badge.bg-primary-subtle');
        const linhas = document.querySelectorAll('tbody tr[data-evento-id]');
        if (badge) {
            const quantidade = linhas.length;
            const texto = `${quantidade} pendência${quantidade === 1 ? '' : 's'} aberta${quantidade === 1 ? '' : 's'}`;
            badge.innerHTML = `<i class="mdi mdi-timer-sand"></i> ${texto}`;
        }

        if (Array.isArray(window.__PENDENCIAS__)) {
            window.__PENDENCIAS__ = window.__PENDENCIAS__.filter((item) => {
                return document.querySelector(`tr[data-evento-id="${item.id}"]`) !== null;
            });
        }

        if (linhas.length === 0) {
            const tabela = document.querySelector('.table-responsive');
            if (tabela) {
                tabela.outerHTML = `
                    <div class="empty-state text-center py-5">
                        <i class="mdi mdi-check-circle-outline"></i>
                        <h5>Todas as pendências foram concluídas</h5>
                        <p>Assim que o RH registrar novos eventos, eles aparecerão por aqui.</p>
                    </div>
                `;
            }
        }
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

            atualizarBadgePendencias();
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
})();
