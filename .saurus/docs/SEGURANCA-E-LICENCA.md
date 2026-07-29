# Segurança, distribuição e licença

## Segurança de release

- assinar executáveis, DLLs, helper, launcher, updater e instalador;
- manter certificado e senha somente em secrets protegidos;
- fixar hashes de dependências externas;
- publicar manifesto assinado;
- não executar downloads sem validar hash e assinatura;
- não incluir senha permanente no motor;
- não registrar credenciais em logs;
- usar rollout piloto e rollback.

## RustDesk e AGPL

O RustDesk 1.4.9 é distribuído sob AGPL-3.0 no repositório upstream. Um fork modificado precisa preservar avisos e cumprir as obrigações da licença aplicáveis ao modo de uso e distribuição. Em particular, a Saurus deve organizar a entrega do código-fonte correspondente das modificações para os destinatários abrangidos e manter a licença/atribuições. Este documento não substitui uma avaliação jurídica.

O nome e os elementos visuais Saurus pertencem à Saurus. Não remova os avisos do código upstream nem represente o fork como produto oficial do projeto RustDesk.

## Fonte correspondente

Recomenda-se manter um repositório de release com:

- commit exato do upstream;
- submódulos;
- scripts de customização;
- workflow e versões de toolchain;
- branding distribuído;
- instruções reproduzíveis;
- avisos de licença;
- patches e código do helper/launcher usados pela versão publicada.


## Política operacional de senha fixa

Por requisito operacional da Saurus, todas as instalações utilizam a senha permanente `ophd0202`. O motor a reaplica ao iniciar o serviço e rejeita outros valores. Essa decisão facilita o atendimento, mas amplia o impacto de eventual divulgação da senha; por isso, o acesso deve permanecer restrito à rede/infraestrutura autorizada, com logs, controle de distribuição e revisão periódica desta política.
