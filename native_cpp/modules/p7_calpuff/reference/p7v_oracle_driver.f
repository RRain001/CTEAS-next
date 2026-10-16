c-----------------------------------------------------------------------
      program p7v_oracle
c-----------------------------------------------------------------------
c
c --- CTEAS P7V FORTRAN ORACLE DRIVER -- hand written for this test
c     harness. This file is NOT vendor source and is never used by the
c     model; it drives the UNMODIFIED vendor units extracted by
c     reference/p7v_source_anchor.py: ZFIND, ADVWND, ADVECT, PUFFDZ.
c
c --- POWLAW (METFM 2/3) and XTPRF (METFM 4/5) are off the locked deck's
c     path (METFM=1) and are hard-failing stubs here.
c
c --- Input on stdin, list directed:
c     line 1: mode
c     mode 1: icase nz zface(1..nz+1) z          -> ilayer
c     mode 2: icase nz zface(1..nz+1) u(1..nz) v(1..nz) zbot ztop
c             -> uave vave
c     mode 3: icase nz zface(1..nz+1) u(1..nz) v(1..nz) zbot ztop
c             -> uadv vadv
c     mode 4: icase icode lpuff istab ilayer htmet dpbl sigzb sigze
c             ziold zimax zface(ilayer) zface(ilayer+1) nspec qm(1) qu(1)
c             -> ztop zbot
c-----------------------------------------------------------------------
      include 'params.puf'
      include 'gen.puf'
      include 'grid.puf'
      include 'puff.puf'
      include 'slug.puf'
      include 'comparm.puf'
      include 'methr.puf'
c
      integer mode,ios,icase,nz_i,ilayer_o,icode_i,istab_i,ilayer_i
      integer ii,kk,nspec_i
      real quval_i
      real zf(200),z_i,u_i(200),v_i(200),zbot_i,ztop_i
      real uave_o,vave_o,uadv_o,vadv_o
      logical lpuff_i
      real htmet_i,dpbl_i,sigzb_i,sigze_i,ziold_i,zimax_i
c
      read(*,*,iostat=ios) mode
      if(ios.ne.0) stop 'P7V oracle: missing mode'
c
      if(mode.eq.1)then
 10      read(*,*,iostat=ios) icase,nz_i
         if(ios.ne.0) goto 999
         read(*,*,iostat=ios) (zf(kk),kk=1,nz_i+1)
         read(*,*,iostat=ios) z_i
         call zfind(z_i,zf,nz_i+1,ilayer_o)
         write(*,'(i8,1x,i8)') icase,ilayer_o
         goto 10
      endif
c
      if(mode.eq.2 .OR. mode.eq.3)then
 20      read(*,*,iostat=ios) icase,nz_i
         if(ios.ne.0) goto 999
         read(*,*,iostat=ios) (zf(kk),kk=1,nz_i+1)
         read(*,*,iostat=ios) (u_i(kk),kk=1,nz_i)
         read(*,*,iostat=ios) (v_i(kk),kk=1,nz_i)
         read(*,*,iostat=ios) zbot_i,ztop_i
         if(mode.eq.2)then
            call advwnd(u_i,v_i,zf,nz_i+1,zbot_i,ztop_i,uave_o,vave_o)
            write(*,'(i8,2(1x,es20.12))') icase,uave_o,vave_o
         else
            nz=nz_i
            nzp1=nz_i+1
            do kk=1,nz_i+1
               zface(kk)=zf(kk)
            enddo
            do kk=1,nz_i
               umet(1,1,kk,1)=u_i(kk)
               vmet(1,1,kk,1)=v_i(kk)
            enddo
            metfm=1
            plexp=0.5
            call advect(.FALSE.,1,1,1,0.1,0.0,231.0,4,70.8,zbot_i,
     &                  ztop_i,uadv_o,vadv_o)
            write(*,'(i8,2(1x,es20.12))') icase,uadv_o,vadv_o
         endif
         goto 20
      endif
c
 30   continue
      read(*,*,iostat=ios) icase,icode_i,lpuff_i,istab_i,ilayer_i,
     &                     htmet_i,dpbl_i,sigzb_i,sigze_i,ziold_i,
     &                     zimax_i,zbot_i,ztop_i,nspec_i,quval_i
      if(ios.ne.0) goto 999
      ii=1
      icode=icode_i
      sigzb(1)=sigzb_i
      sigze(1)=sigze_i
      ziold(1)=ziold_i
      zimax(1)=zimax_i
      zface(ilayer_i)=zbot_i
      zface(ilayer_i+1)=ztop_i
      nspec=nspec_i
      do kk=1,nspec_i
         qm(kk,1)=1.0
         qu(kk,1)=quval_i
      enddo
      call puffdz(1,icode_i,lpuff_i,istab_i,ilayer_i,htmet_i,dpbl_i,
     &            ztop_i,zbot_i)
      write(*,'(i8,2(1x,es20.12))') icase,ztop_i,zbot_i
      goto 30
c
 999  continue
      end
c-----------------------------------------------------------------------
      subroutine powlaw(zref,z0,ws0,pexp,ws)
c-----------------------------------------------------------------------
      real zref,z0,ws0,pexp,ws
      write(*,*) 'P7V oracle: POWLAW must not be called (METFM 2/3)'
      stop 9
      end
c-----------------------------------------------------------------------
      subroutine xtprf(nzprf,zprf2,xprf,zref,chr,z0m,el,dpbl,istab,
     &                 ptg,out,problem)
c-----------------------------------------------------------------------
      integer nzprf,istab
      real zprf2(*),xprf(*),zref,z0m,el,dpbl,ptg(*),out
      character*3 chr
      logical problem
      write(*,*) 'P7V oracle: XTPRF must not be called (METFM 4/5)'
      stop 9
      end
