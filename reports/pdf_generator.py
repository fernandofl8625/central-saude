import io
import re
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


class PDFReportGenerator:
    def __init__(self):
        pass

    def _limpar_markdown_para_reportlab(self, texto: str) -> str:
        """Converte marcações Markdown brutas para tags HTML simples aceitas pelo ReportLab."""
        if not texto:
            return ""

        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"
            "\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF"
            "\U00002700-\U000027BF"
            "\U0001F900-\U0001F9FF"
            "\U0001FA70-\U0001FAFF"
            "]+", flags=re.UNICODE
        )
        texto = emoji_pattern.sub('', texto)

        texto = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', texto)
        texto = re.sub(r'`(.*?)`', r'<i>\1</i>', texto)
        texto = re.sub(r'#{1,6}\s*(.*?)\n', r'<br/><b>\1</b><br/>', texto)
        texto = texto.replace('\n', '<br/>')
        return texto

    def _gerar_grafico_readiness_buffer(self, df_telemetria: pd.DataFrame) -> io.BytesIO:
        """Gera a imagem do gráfico de evolução do Readiness usando Matplotlib em memória."""
        try:
            df = df_telemetria.sort_values(by="DataRegistro").copy()
            df['DataRegistro'] = pd.to_datetime(df['DataRegistro'])

            fig, ax = plt.subplots(figsize=(6.5, 2.2), dpi=150)
            fig.patch.set_facecolor('#F8FAFC')
            ax.set_facecolor('#FFFFFF')

            if 'ScoreProntitudade' in df.columns:
                ax.plot(df['DataRegistro'], df['ScoreProntitudade'], label='Readiness',
                        color='#38BDF8', linewidth=2, marker='o', markersize=3)
            if 'QualidadeSonoScore' in df.columns:
                ax.plot(df['DataRegistro'], df['QualidadeSonoScore'],
                        label='Score Sono', color='#3B82F6', linewidth=1.5, linestyle='--')
            if 'NivelEnergiaScore' in df.columns:
                ax.plot(df['DataRegistro'], df['NivelEnergiaScore'],
                        label='Energia', color='#10B981', linewidth=1.5, linestyle=':')

            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.set_title("Evolucao da Prontidao (Readiness) & Qualidade de Sono",
                         fontsize=9, fontweight='bold', color='#1E293B')
            ax.tick_params(axis='both', which='major',
                           labelsize=7, labelcolor='#475569')
            ax.grid(True, linestyle=':', alpha=0.6, color='#CBD5E1')
            ax.legend(loc='lower right', fontsize=7, frameon=True,
                      facecolor='#F8FAFC', edgecolor='none')

            plt.tight_layout()
            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png', bbox_inches='tight')
            plt.close(fig)
            img_buffer.seek(0)
            return img_buffer
        except Exception:
            return None

    def gerar_pdf_saude_completo(self, df_telemetria: pd.DataFrame, df_exames: pd.DataFrame, parecer_ia: str = "", metas_user: dict = None, **kwargs) -> bytes:
        """Gera um PDF completo refletindo todas as seções do Dashboard."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36,
                                leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        styles = getSampleStyleSheet()

        style_title = ParagraphStyle(
            'DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#1E293B"))
        style_sub = ParagraphStyle(
            'DocSub', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor("#64748B"))
        style_h2 = ParagraphStyle('SectionH2', parent=styles['Heading2'], fontSize=11, leading=15, textColor=colors.HexColor(
            "#0F172A"), spaceBefore=10, spaceAfter=6)
        style_body = ParagraphStyle(
            'DocBody', parent=styles['Normal'], fontSize=8.5, leading=12, textColor=colors.HexColor("#334155"))
        style_ia = ParagraphStyle('IABody', parent=styles['Normal'], fontSize=8, leading=11, textColor=colors.HexColor(
            "#0F172A"), backColor=colors.HexColor("#F1F5F9"), borderPadding=8)

        # CABEÇALHO DO DOCUMENTO
        story.append(
            Paragraph("Relatorio Integrado de Telemetria & Saude", style_title))
        story.append(Paragraph(
            f"Emissao: {datetime.now().strftime('%d/%m/%Y as %H:%M')} | Central de Comando", style_sub))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1,
                     color=colors.HexColor("#CBD5E1"), spaceAfter=10))

        # 1. PARECER DA IA
        if parecer_ia:
            story.append(
                Paragraph("Parecer do Assistente Virtual de Saude & Fisiologia", style_h2))
            texto_formatado = self._limpar_markdown_para_reportlab(parecer_ia)
            story.append(Paragraph(texto_formatado, style_ia))
            story.append(Spacer(1, 10))

        if not df_telemetria.empty:
            df_7 = df_telemetria.head(7)
            med_passos = int(df_7['Passos'].fillna(0).mean())
            med_sono = round(df_7['HorasSono'].fillna(0).mean(), 1)
            med_score = int(df_7['QualidadeSonoScore'].fillna(0).mean())
            med_profundo = int(df_7['SonoProfundoMinutos'].fillna(
                60).mean()) if 'SonoProfundoMinutos' in df_7.columns else 60
            med_rem = int(df_7['SonoREMMinutos'].fillna(
                90).mean()) if 'SonoREMMinutos' in df_7.columns else 90
            med_readiness = int(df_7['ScoreProntitudade'].fillna(
                75).mean()) if 'ScoreProntitudade' in df_7.columns else 75
            med_spo2 = round(df_7['SpO2MedioPct'].fillna(
                96.5).mean(), 1) if 'SpO2MedioPct' in df_7.columns else 96.5
            med_agua = int(df_7['ConsumoAguaML'].fillna(0).mean())
            med_cafe = int(df_7['ConsumoCafeML'].fillna(0).mean())
            med_cafeina = int(df_7['ConsumoCafeinaMG'].fillna(0).mean())
            med_fc = int(df_7['FrequenciaCardiacaRepouso'].fillna(0).mean())
            med_estresse = int(df_7['NivelEstresseScore'].fillna(0).mean())

            m_passos = metas_user.get(
                'meta_passos', 8000) if metas_user else 8000
            m_sono = metas_user.get(
                'meta_sono_horas', 7.0) if metas_user else 7.0
            m_score = metas_user.get(
                'meta_score_sono', 75) if metas_user else 75
            lim_cafe = metas_user.get(
                'limite_cafe_ml', 300) if metas_user else 300

            # 2. RESUMO EXECUTIVO
            story.append(
                Paragraph("1. Resumo Executivo & Fisiologia (Media 7 Dias)", style_h2))
            dados_tab = [
                ["Metrica", "Media Registrada", "Meta Personalizada", "Status"],
                ["Readiness Score", f"{med_readiness} / 100", "> 75 / 100",
                    "Excelente" if med_readiness >= 75 else "Atencao"],
                ["Passos Diarios", f"{med_passos:,}", f"{m_passos:,} passos",
                    "Adequado" if med_passos >= m_passos else "Abaixo"],
                ["Sono Total", f"{med_sono}h / noite", f"{m_sono}h / noite",
                    "Adequado" if med_sono >= m_sono else "Privacao"],
                ["Sono Profundo / REM", f"{med_profundo}m / {med_rem}m",
                    "> 60m / > 90m", "Equilibrado" if med_profundo >= 45 else "Baixo"],
                ["Sat. Oxigenio (SpO2)", f"{med_spo2} %", "> 95.0 %",
                 "Normal" if med_spo2 >= 95 else "Atencao"],
                ["FC em Repouso", f"{med_fc} BPM", "60 - 80 BPM",
                    "Normal" if 60 <= med_fc <= 80 else "Fora da Faixa"],
                ["Hidratacao Total", f"{med_agua} ml", "2.500 ml",
                    "Ideal" if med_agua >= 2500 else "Abaixo"],
                ["Cafeina Estimada", f"{med_cafeina} mg", "< 300 mg",
                    "Controlado" if med_cafeina <= 300 else "Elevado"],
                ["Nivel de Estresse", f"{med_estresse} / 100", "< 40 / 100",
                    "Baixo" if med_estresse < 40 else "Moderado/Alto"]
            ]

            t = Table(dados_tab, colWidths=[130, 130, 130, 130])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ]))
            story.append(t)
            story.append(Spacer(1, 10))

            # 3. GRÁFICO GERADO DINAMICAMENTE NO PDF
            img_buf = self._gerar_grafico_readiness_buffer(df_telemetria)
            if img_buf:
                story.append(
                    Paragraph("2. Tendencia Temporal da Prontidao & Bateria Corporal", style_h2))
                story.append(Image(img_buf, width=520, height=176))
                story.append(Spacer(1, 10))

            # 4. DIÁRIO SINTOMÁTICO
            med_disp = round(df_7['DisposicaoAcordarScore'].fillna(
                5).mean(), 1) if 'DisposicaoAcordarScore' in df_7.columns else 5.0
            med_foco = round(df_7['FocoClarezaScore'].fillna(
                5).mean(), 1) if 'FocoClarezaScore' in df_7.columns else 5.0
            med_dor = round(df_7['DorMuscularScore'].fillna(
                0).mean(), 1) if 'DorMuscularScore' in df_7.columns else 0.0
            med_dig = round(df_7['ConfortoDigestivoScore'].fillna(
                8).mean(), 1) if 'ConfortoDigestivoScore' in df_7.columns else 8.0

            story.append(
                Paragraph("3. Media do Diario Sintomatico (Ultimos 7 Dias)", style_h2))
            dados_sint = [
                ["Disposicao ao Acordar", "Foco & Clareza",
                    "Dor Muscular (DOMS)", "Conforto Digestivo"],
                [f"{med_disp} / 10", f"{med_foco} / 10",
                    f"{med_dor} / 10", f"{med_dig} / 10"]
            ]
            t_sint = Table(dados_sint, colWidths=[130, 130, 130, 130])
            t_sint.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#334155")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ]))
            story.append(t_sint)
            story.append(Spacer(1, 10))

            # 5. CRONOGRAMA SEMANAL RECOMENDADO
            story.append(Paragraph(
                "4. Cronograma Semanal Recomendado (Exercicios & Habitos)", style_h2))
            dados_crono = [
                ["Dia", "Modalidade Sugerida", "Foco da Sessao", "Meta de Agua"],
                ["Segunda", "Musculacao",
                    "Membros Superiores + Cardio 15min", "2.500 ml"],
                ["Terca", "Corrida / Caminhada",
                    "Aerobico Moderado (30-45min)", "3.000 ml"],
                ["Quarta", "Musculacao",
                    "Membros Inferiores (Pernas)", "2.500 ml"],
                ["Quinta", "Descanso Ativo",
                    "Caminhada Leve + Alongamento", "2.500 ml"],
                ["Sexta", "Musculacao", "Full Body / Core", "2.500 ml"],
                ["Sabado", "Ciclismo / Aerobico",
                    "Treino de Lazer / Resistencia", "3.000 ml"],
                ["Domingo", "Descanso Total", "Recuperacao Passiva", "2.500 ml"]
            ]
            t_crono = Table(dados_crono, colWidths=[65, 115, 240, 100])
            t_crono.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ]))
            story.append(t_crono)
            story.append(Spacer(1, 10))

            # 6. COMPOSIÇÃO CORPORAL
            df_peso = df_telemetria[df_telemetria['PesoKG'].notnull()]
            if not df_peso.empty:
                ult_b = df_peso.iloc[0]
                story.append(
                    Paragraph("5. Analise Corporal & Metabolismo", style_h2))
                dados_bio = [
                    ["Peso Total", "Musculo Esqueletico",
                        "Massa Gorda", "TMB (Basal)"],
                    [f"{ult_b['PesoKG']} kg", f"{ult_b.get('MusculoEsqueleticoKG') or 'N/A'} kg",
                     f"{ult_b.get('MassaGordaKG') or 'N/A'} kg", f"{ult_b.get('TMBKcal') or 'N/A'} kcal"]
                ]
                t_bio = Table(dados_bio, colWidths=[130, 130, 130, 130])
                t_bio.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#334155")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ]))
                story.append(t_bio)
                story.append(Spacer(1, 10))

        # 7. EXAMES LABORATORIAIS
        if not df_exames.empty:
            story.append(
                Paragraph("6. Marcadores Laboratoriais Recentes", style_h2))
            ult_data = df_exames['data_exame'].iloc[0]
            df_ult = df_exames[df_exames['data_exame'] == ult_data].head(12)

            dados_ex = [["Marcador", "Resultado",
                         "Unidade", "Referencia Min/Max"]]
            for _, r in df_ult.iterrows():
                ref_str = f"{r['referencia_min'] or '-'} - {r['referencia_max'] or '-'}"
                dados_ex.append([str(r['marcador']), str(
                    r['resultado']), str(r['unidade']), ref_str])

            t_ex = Table(dados_ex, colWidths=[160, 120, 100, 140])
            t_ex.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ]))
            story.append(t_ex)
            story.append(Spacer(1, 10))

        # 8. DIRETRIZES
        story.append(
            Paragraph("7. Diretrizes e Recomendacoes Praticas (OMS & ACSM)", style_h2))
        diretrizes_text = """
        • <b>Frequencia Semanal:</b> Praticar pelo menos 150 minutos de atividade moderada por semana.<br/>
        • <b>Ingestao Proteica:</b> Garantir de 1.6g a 2.0g de proteina por kg corporal para suporte a massa magra.<br/>
        • <b>Janela de Cafeina:</b> Encerrar bebidas estimulantes de 6 a 8 horas antes de deitar.
        """
        story.append(Paragraph(diretrizes_text, style_body))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def gerar_dossie_clinico_pdf(self, dados_ficha: dict, df_biometria: pd.DataFrame, sups_ativos: list, df_exames: pd.DataFrame) -> bytes:
        """Gera um PDF médico compacto de 1 página formatado para consultas."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'DocSubTitle',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#475569'),
            spaceAfter=10
        )
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#1E293B'),
            spaceBefore=8,
            spaceAfter=6
        )
        text_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#334155')
        )
        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )

        elements = []

        # 1. Cabeçalho
        elements.append(
            Paragraph("DOSSIE CLINICO & RESUMO DE SAUDE", title_style))
        data_emissao = datetime.now().strftime('%d/%m/%Y as %H:%M')
        elements.append(
            Paragraph(f"Emissao: {data_emissao} | Telemetria Integrada", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5,
                        color=colors.HexColor('#2563EB'), spaceAfter=8))

        # 2. Ficha Médica
        elements.append(
            Paragraph("1. Ficha Medica do Paciente", section_style))
        t_ficha_data = [
            [
                Paragraph(
                    f"<b>Tipo Sanguineo:</b> {dados_ficha.get('tipo_sanguineo', 'N/I')}", text_style),
                Paragraph(
                    f"<b>Plano de Saude:</b> {dados_ficha.get('plano_saude', 'N/I')}", text_style)
            ],
            [
                Paragraph(
                    f"<b>Alergias:</b> {dados_ficha.get('alergias', 'Nenhuma')}", text_style),
                Paragraph(
                    f"<b>Condicoes Cronicas:</b> {dados_ficha.get('condicoes_cronicas', 'Nenhuma')}", text_style)
            ],
            [
                Paragraph(
                    f"<b>Historico Familiar:</b> {dados_ficha.get('historico_familiar', 'N/I')}", text_style),
                Paragraph(
                    f"<b>Emergencia:</b> {dados_ficha.get('contato_emergencia', 'N/I')}", text_style)
            ]
        ]
        t_ficha = Table(t_ficha_data, colWidths=[3.75*72, 3.75*72])
        t_ficha.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_ficha)
        elements.append(Spacer(1, 8))

        # 3. Composição Corporal Recente
        elements.append(
            Paragraph("2. Biometria & Composicao Corporal Recente", section_style))
        if not df_biometria.empty and 'PesoKG' in df_biometria.columns:
            df_p = df_biometria[df_biometria['PesoKG'].notnull()]
            if not df_p.empty:
                ult = df_p.iloc[0]
                t_bio_data = [
                    [
                        Paragraph("<b>Data</b>", table_header_style),
                        Paragraph("<b>Peso (kg)</b>", table_header_style),
                        Paragraph("<b>Gordura (%)</b>", table_header_style),
                        Paragraph("<b>Musculo (kg)</b>", table_header_style),
                        Paragraph("<b>Massa Gorda (kg)</b>",
                                  table_header_style),
                        Paragraph("<b>Agua (kg)</b>", table_header_style),
                        Paragraph("<b>TMB (kcal)</b>", table_header_style)
                    ],
                    [
                        Paragraph(
                            str(ult.get('DataRegistro', '-')), text_style),
                        Paragraph(f"{ult.get('PesoKG', 0):.1f}", text_style),
                        Paragraph(
                            f"{ult.get('PercentualGordura', 0):.1f}%", text_style),
                        Paragraph(
                            f"{ult.get('MusculoEsqueleticoKG', 0):.1f}", text_style),
                        Paragraph(
                            f"{ult.get('MassaGordaKG', 0):.1f}", text_style),
                        Paragraph(
                            f"{ult.get('AguaCorporalKG', 0):.1f}", text_style),
                        Paragraph(
                            f"{int(ult.get('TMBKcal', 0) or 0)}", text_style)
                    ]
                ]
                t_bio = Table(t_bio_data, colWidths=[
                              1.1*72, 1.0*72, 1.0*72, 1.1*72, 1.2*72, 1.0*72, 1.1*72])
                t_bio.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                    ('PADDING', (0, 0), (-1, -1), 3),
                ]))
                elements.append(t_bio)
        elements.append(Spacer(1, 8))

        # 4. Suplementos & Medicamentos Ativos
        elements.append(
            Paragraph("3. Protocolo Ativo de Suplementos & Medicamentos", section_style))
        if sups_ativos:
            t_sup_data = [[
                Paragraph("<b>Item / Farmaco</b>", table_header_style),
                Paragraph("<b>Dose</b>", table_header_style),
                Paragraph("<b>Horario</b>", table_header_style),
                Paragraph("<b>Classe / Acao</b>", table_header_style)
            ]]
            for s in sups_ativos:
                t_sup_data.append([
                    Paragraph(s['nome'], text_style),
                    Paragraph(s['dose'], text_style),
                    Paragraph(s['horario'], text_style),
                    Paragraph(s.get('categoria_acao', 'Geral'), text_style)
                ])
            t_sup = Table(t_sup_data, colWidths=[
                          2.5*72, 1.2*72, 1.5*72, 2.3*72])
            t_sup.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t_sup)
        elements.append(Spacer(1, 8))

        # 5. Exames Laboratoriais Recentes
        elements.append(Paragraph(
            "4. Marcadores Laboratoriais Recentes (Sabin/Fleury)", section_style))
        if not df_exames.empty:
            data_rec = df_exames['data_exame'].max()
            df_rec = df_exames[df_exames['data_exame'] == data_rec].head(8)

            t_ex_data = [[
                Paragraph("<b>Marcador</b>", table_header_style),
                Paragraph("<b>Resultado</b>", table_header_style),
                Paragraph("<b>Referencia</b>", table_header_style),
                Paragraph("<b>Status</b>", table_header_style)
            ]]
            for _, r in df_rec.iterrows():
                res = float(r['resultado'])
                rmin = float(r['referencia_min']) if pd.notnull(
                    r['referencia_min']) else None
                rmax = float(r['referencia_max']) if pd.notnull(
                    r['referencia_max']) else None

                status_txt = "Normal"
                if rmin is not None and res < rmin:
                    status_txt = "Abaixo do min."
                elif rmax is not None and res > rmax:
                    status_txt = "Acima do max."

                ref_str = f"{rmin or 0} - {rmax or '∞'} {r['unidade'] or ''}"

                t_ex_data.append([
                    Paragraph(str(r['marcador']), text_style),
                    Paragraph(f"{res} {r['unidade'] or ''}", text_style),
                    Paragraph(ref_str, text_style),
                    Paragraph(status_txt, text_style)
                ])

            t_ex = Table(t_ex_data, colWidths=[2.5*72, 1.5*72, 2.0*72, 1.5*72])
            t_ex.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#F1F5F9')),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(t_ex)

        doc.build(elements)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data
